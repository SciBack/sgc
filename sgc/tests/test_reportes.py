# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de los tres informes del SGC (#38).

Lo que más importa aquí no es el contenido de las columnas, es **cómo
consultan**. Frappe comprueba el permiso de informe sobre el doctype
(`query_report.py:49`) pero no filtra las filas: eso depende del script. Y
`No Conformidad`, `Hallazgo` y `Plan Mejora` tienen aislamiento por ámbito
declarado en `hooks.py:174`.

Un `get_all` colado en un informe daría el mismo resultado en estos tests
—corren como Administrator— y enseñaría los datos de otros programas en un
fichero exportable. Por eso se comprueba sobre el **AST**, no ejecutando: el
fallo tiene que saltar aunque nadie escriba un test de ámbito.

También se comprueba la lógica de lectura, que es donde un informe miente sin
fallar: el retraso vacío que no es cero, el hallazgo que nunca escaló y el
tratamiento que no bajó el nivel.
"""
import ast
import importlib
import inspect

import frappe
from frappe.tests import IntegrationTestCase

from sgc import reportes
from sgc.sgc_auditoria.report.resultados_de_auditoria import resultados_de_auditoria as r_aud
from sgc.sgc_nucleo.report.mejoramiento_continuo import mejoramiento_continuo as r_mej
from sgc.sgc_riesgos.report.matriz_de_riesgos import matriz_de_riesgos as r_rie

MODULOS_INFORME = (r_mej, r_aud, r_rie)


def _llamadas(modulo):
    """Nombres con puntos de todas las llamadas del módulo, vía AST."""
    def puntos(nodo):
        partes = []
        while isinstance(nodo, ast.Attribute):
            partes.append(nodo.attr)
            nodo = nodo.value
        if isinstance(nodo, ast.Name):
            partes.append(nodo.id)
            return list(reversed(partes))
        return []

    arbol = ast.parse(inspect.getsource(modulo))
    return {
        ".".join(puntos(n.func))
        for n in ast.walk(arbol)
        if isinstance(n, ast.Call) and puntos(n.func)
    }


class IntegrationTestReportes(IntegrationTestCase):
    # --- la regla de acceso a datos ----------------------------------------

    def test_ningun_informe_consulta_con_get_all_ni_sql(self):
        """El aislamiento por ámbito depende de esto y no se ve en el resultado."""
        for modulo in MODULOS_INFORME:
            llamadas = _llamadas(modulo)
            nombre = modulo.__name__
            self.assertNotIn("frappe.get_all", llamadas, f"{nombre} usa get_all")
            self.assertNotIn("frappe.db.sql", llamadas, f"{nombre} usa SQL crudo")
            self.assertNotIn("frappe.db.get_all", llamadas, f"{nombre} usa db.get_all")

    def test_el_helper_consulta_con_get_list(self):
        self.assertIn("frappe.get_list", _llamadas(reportes))

    def test_los_informes_existen_como_registro(self):
        for nombre in ("Mejoramiento Continuo", "Resultados de Auditoria", "Matriz de Riesgos"):
            self.assertTrue(
                frappe.db.exists("Report", nombre), f"falta el registro de informe {nombre}"
            )

    def test_cada_informe_declara_columnas_con_fieldname_y_label(self):
        for modulo in MODULOS_INFORME:
            for col in modulo.columnas():
                self.assertTrue(col.get("fieldname"), f"columna sin fieldname en {modulo.__name__}")
                self.assertTrue(col.get("label"), f"columna sin label en {modulo.__name__}")

    def test_execute_devuelve_columnas_y_filas_sin_filtros(self):
        """Con la base como esté: no debe reventar por falta de filtros."""
        for modulo in MODULOS_INFORME:
            columnas, filas = modulo.execute()
            self.assertIsInstance(columnas, list)
            self.assertIsInstance(filas, list)

    # --- la lógica de lectura ----------------------------------------------

    def test_sin_retraso_la_columna_queda_vacia_no_en_cero(self):
        """Un 0 se lee como «vence hoy»; un hueco, como «no aplica»."""
        from frappe.utils import add_days, nowdate

        self.assertIsNone(reportes.dias_de_retraso(add_days(nowdate(), 5)))
        self.assertIsNone(reportes.dias_de_retraso(None))
        self.assertEqual(reportes.dias_de_retraso(add_days(nowdate(), -3)), 3)

    def test_una_accion_cerrada_no_acumula_retraso(self):
        from frappe.utils import add_days, nowdate

        vencida = add_days(nowdate(), -10)
        self.assertEqual(reportes.dias_de_retraso(vencida), 10)
        self.assertIsNone(reportes.dias_de_retraso(vencida, cerrado=True))

    def test_una_no_conformidad_sin_escalar_sale_marcada(self):
        pendiente = r_aud._escalo({"tipo": "No conformidad mayor", "no_conformidad": None})
        escalada = r_aud._escalo({"tipo": "No conformidad mayor", "no_conformidad": "NC-1"})
        observacion = r_aud._escalo({"tipo": "Observacion", "no_conformidad": None})

        self.assertEqual(pendiente, "PENDIENTE")
        self.assertEqual(escalada, "NC-1")
        self.assertEqual(observacion, "—", "una observación no tiene por qué escalar")

    def test_el_efecto_del_tratamiento_distingue_los_tres_casos(self):
        sin_tratar = r_rie._efecto("Alto", None, hay_tratamiento=False)
        no_bajo = r_rie._efecto("Alto", "Alto", hay_tratamiento=True)
        bajo = r_rie._efecto("Extremo", "Moderado", hay_tratamiento=True)

        self.assertEqual(sin_tratar, "SIN TRATAMIENTO")
        self.assertEqual(no_bajo, "NO BAJÓ")
        self.assertIn("2", bajo, "de Extremo a Moderado son dos niveles")

    def test_un_riesgo_bajo_sin_tratar_no_se_marca_como_problema(self):
        """No todo riesgo necesita tratamiento: marcarlos todos sería ruido."""
        self.assertEqual(r_rie._efecto("Bajo", None, hay_tratamiento=False), "—")

    # --- el origen de una acción -------------------------------------------

    def test_el_origen_prefiere_la_no_conformidad(self):
        """Es el vínculo formal que exige la norma; el plan agrupa y es el último recurso."""
        fila = {"no_conformidad": "NC-1", "hallazgo": "H-1", "plan_mejora": "P-1"}
        self.assertIn("NC-1", r_mej._origen(fila))
        self.assertIn("H-1", r_mej._origen({"hallazgo": "H-1", "plan_mejora": "P-1"}))
        self.assertIn("P-1", r_mej._origen({"plan_mejora": "P-1"}))
        self.assertIn("Sin origen", r_mej._origen({}))

    def test_los_modulos_de_informe_se_importan(self):
        """Un informe estándar que no importa es un informe que no existe."""
        for ruta in (
            "sgc.sgc_nucleo.report.mejoramiento_continuo.mejoramiento_continuo",
            "sgc.sgc_auditoria.report.resultados_de_auditoria.resultados_de_auditoria",
            "sgc.sgc_riesgos.report.matriz_de_riesgos.matriz_de_riesgos",
        ):
            self.assertTrue(hasattr(importlib.import_module(ruta), "execute"))
