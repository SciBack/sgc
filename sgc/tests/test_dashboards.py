# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.setup.f21_dashboards` y `sgc.dashboards` — cuadros de mando (#30).

Cubre que `run()`:
- Crea las 7 tarjetas y los 5 gráficos, y es **idempotente** (el fallo que este
  test previene es real: `Number Card` no tiene autoname, así que sin asignar
  `doc.name` Frappe le pone un hash y cada migrate crearía una tarjeta nueva).
- No crea **ningún** gráfico de tipo Heatmap, ni siquiera si alguien lo añade a
  la lista: ese tipo consulta con `get_all` e ignora permisos
  (`dashboard_chart.py:245`).
- Declara `module` en todo, que es de lo que depende el filtrado por permisos.

Y que los métodos de `sgc.dashboards`:
- Cuentan lo vencido y **solo** lo vencido: un documento con plazo futuro, uno
  ya cerrado y uno sin fecha no cuentan.
- Consultan con `get_list`, que aplica `permission_query_conditions`. Se
  comprueba mirando el código, no solo el resultado: un `get_all` colado daría
  el mismo número en el test (que corre como Administrator) y expondría datos
  en producción.

Gotcha (patrón de f7/f11/f15): `run()` deja `frappe.flags.in_patch = True` sin
resetear. El tearDown lo apaga para no contaminar tests posteriores.
"""
import ast
import inspect

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc import dashboards
from sgc.setup import f21_dashboards as f21

PREFIJO = "TEST-DASH"


class IntegrationTestDashboards(IntegrationTestCase):
    def tearDown(self):
        frappe.flags.in_patch = False

    # --- creación e idempotencia -------------------------------------------

    def test_crea_todas_las_tarjetas_y_graficos(self):
        f21.run()
        for cfg in f21.NUMBER_CARDS:
            self.assertTrue(
                frappe.db.exists("Number Card", cfg["name"]), f"falta la tarjeta {cfg['name']}"
            )
        for cfg in f21.CHARTS:
            self.assertTrue(
                frappe.db.exists("Dashboard Chart", cfg["chart_name"]),
                f"falta el gráfico {cfg['chart_name']}",
            )

    def test_reejecutar_no_duplica(self):
        """El fallo que este test previene: Number Card sin autoname."""
        f21.run()
        antes_cards = frappe.db.count("Number Card")
        antes_charts = frappe.db.count("Dashboard Chart")
        f21.run()
        self.assertEqual(frappe.db.count("Number Card"), antes_cards)
        self.assertEqual(frappe.db.count("Dashboard Chart"), antes_charts)

    def test_todo_declara_modulo(self):
        """Sin `module`, el filtrado por permisos de Frappe no puede acotar."""
        for cfg in f21.NUMBER_CARDS:
            self.assertTrue(cfg.get("module"), f"{cfg['name']} sin módulo")
        for cfg in f21.CHARTS:
            self.assertTrue(cfg.get("module"), f"{cfg['chart_name']} sin módulo")

    # --- la restricción del heatmap ----------------------------------------

    def test_ningun_grafico_declarado_es_heatmap(self):
        for cfg in f21.CHARTS:
            self.assertNotIn(
                cfg["type"],
                f21.TIPOS_PROHIBIDOS,
                f"{cfg['chart_name']} usa {cfg['type']}, que ignora permisos",
            )

    def test_run_rechaza_un_heatmap_anadido_a_mano(self):
        """Defensa en profundidad: si alguien lo añade a la lista, run() falla."""
        original = list(f21.CHARTS)
        f21.CHARTS.append(
            {
                "chart_name": f"{PREFIJO} heatmap",
                "document_type": "No Conformidad",
                "module": "SGC Nucleo",
                "chart_type": "Count",
                "type": "Heatmap",
                "filters": [],
            }
        )
        try:
            with self.assertRaises(frappe.ValidationError):
                f21.run()
        finally:
            f21.CHARTS[:] = original
            frappe.db.rollback()

    # --- los métodos de cálculo --------------------------------------------

    def test_los_metodos_consultan_con_get_list_no_get_all(self):
        """El aislamiento por ámbito depende de esto, y no se ve en el resultado.

        Un `get_all` colado devolvería el mismo número en este test (corre como
        Administrator) y expondría documentos de otros ámbitos en producción.

        Se analiza el AST y no el texto: el módulo **menciona** `get_all` en su
        docstring, precisamente para explicar por qué no lo usa. Un test sobre el
        texto fallaría por esa mención y empujaría a borrar la explicación, que
        es lo contrario de lo que interesa.
        """
        arbol = ast.parse(inspect.getsource(dashboards))
        llamadas = {
            ".".join(self._puntos(n.func))
            for n in ast.walk(arbol)
            if isinstance(n, ast.Call) and self._puntos(n.func)
        }
        self.assertIn("frappe.get_list", llamadas)
        self.assertNotIn("frappe.get_all", llamadas)
        self.assertNotIn("frappe.db.count", llamadas)

    @staticmethod
    def _puntos(nodo):
        """Devuelve ['frappe','db','count'] para una llamada con puntos."""
        partes = []
        while isinstance(nodo, ast.Attribute):
            partes.append(nodo.attr)
            nodo = nodo.value
        if isinstance(nodo, ast.Name):
            partes.append(nodo.id)
            return list(reversed(partes))
        return []

    def test_accion_vencida_cuenta_y_las_demas_no(self):
        base = dashboards.acciones_vencidas()

        vencida = self._accion(fecha=add_days(nowdate(), -5), estado="En ejecucion")
        self.assertEqual(dashboards.acciones_vencidas(), base + 1)

        # Con plazo futuro: no está vencida.
        self._accion(fecha=add_days(nowdate(), 5), estado="En ejecucion")
        self.assertEqual(dashboards.acciones_vencidas(), base + 1)

        # Sin fecha de compromiso: no tiene plazo que incumplir.
        self._accion(fecha=None, estado="En ejecucion")
        self.assertEqual(dashboards.acciones_vencidas(), base + 1)

        # Vencida pero ya verificada: deja de contar.
        vencida.reload()
        vencida.db_set("estado", "Verificada eficaz")
        self.assertEqual(dashboards.acciones_vencidas(), base)

    def test_documentos_por_revisar_incluye_los_ya_vencidos(self):
        """Un documento con la revisión pasada es más urgente, no menos."""
        base = dashboards.documentos_por_revisar()
        self._documento(fecha_revision=add_days(nowdate(), -10))
        self.assertEqual(dashboards.documentos_por_revisar(), base + 1)

    def test_documento_con_revision_lejana_no_cuenta(self):
        base = dashboards.documentos_por_revisar()
        self._documento(fecha_revision=add_days(nowdate(), 90))
        self.assertEqual(dashboards.documentos_por_revisar(), base)

    # --- helpers ------------------------------------------------------------

    def _accion(self, fecha, estado):
        doc = frappe.get_doc(
            {
                "doctype": "Accion Mejora",
                "codigo": frappe.generate_hash(length=10),
                "descripcion": f"{PREFIJO} acción",
                "tipo": "Correctiva",
                "estado": "Planificada",
            }
        )
        doc.flags.ignore_permissions = True
        doc.insert(ignore_mandatory=True)
        # El estado y la fecha se fijan por db_set para no pelear con las
        # validaciones de transición de accion_mejora.py, que no son objeto de
        # este test.
        doc.db_set("fecha_compromiso", fecha)
        doc.db_set("estado", estado)
        return doc

    def _documento(self, fecha_revision):
        doc = frappe.get_doc(
            {
                "doctype": "Documento Controlado",
                "titulo": f"{PREFIJO} documento",
                "tipo_documento": "Formato",
            }
        )
        doc.flags.ignore_permissions = True
        doc.insert(ignore_mandatory=True)
        doc.db_set("fecha_proxima_revision", fecha_revision)
        doc.db_set("estado", "Publicado")
        return doc
