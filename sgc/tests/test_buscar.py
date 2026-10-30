# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Buscar «gestion» tiene que encontrar «Gestión».

En castellano casi todo lleva tilde y la búsqueda de Frappe compara el texto tal
cual, así que `LIKE '%gestion%'` no encuentra «Gestión». Medido en producción el
2026-08-24 sobre los 22 procesos: «gestion» daba 0 resultados y «gestión» daba
10.

El efecto es peor que el número, porque quien busca no sabe que el problema es
la tilde: escribe «tecnolog», no aparece «Gestión tecnológica» —la `ó` corta la
coincidencia a mitad de palabra— y concluye que el buscador está roto. La
persona que lo probó llegó a teclear la tilde a mano para que apareciera, y ahí
se topó además con un fallo de composición del teclado.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.buscar import enlaces


def _buscar(txt, doctype="Proceso"):
    return enlaces(doctype, txt, "name", 0, 20, None)


class IntegrationTestBuscar(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.sufijo = frappe.generate_hash(length=8)
        self.proceso = frappe.get_doc({
            "doctype": "Proceso",
            "codigo": f"BUS-{frappe.generate_hash(length=5)}",
            "proceso": f"Gestión{self.sufijo} TecnolóG{self.sufijo} de prueba",
        }).insert(ignore_permissions=True)

    def _codigos(self, filas):
        return [f[0] for f in filas]

    # ------------------------------------------------------------------
    def test_encuentra_sin_tilde(self):
        """El caso que motivó todo esto."""
        self.assertIn(self.proceso.name, self._codigos(_buscar(f"gestion{self.sufijo}")))

    def test_encuentra_con_tilde(self):
        """Y quien la escribe bien no queda peor que quien no."""
        self.assertIn(self.proceso.name, self._codigos(_buscar(f"gestión{self.sufijo}")))

    def test_encuentra_a_mitad_de_palabra(self):
        """«tecnolog» corta «tecnológica» justo en la tilde."""
        self.assertIn(self.proceso.name, self._codigos(_buscar(f"tecnolog{self.sufijo}")))

    def test_ignora_mayusculas(self):
        self.assertIn(self.proceso.name, self._codigos(_buscar(f"GESTION{self.sufijo.upper()}")))

    def test_busca_tambien_por_codigo(self):
        """Quien se sabe el código lo escribe y va más rápido."""
        self.assertIn(self.proceso.name, self._codigos(_buscar(self.proceso.name)))

    def test_texto_vacio_devuelve_el_catalogo(self):
        """Al abrir el desplegable sin escribir hay que ver algo."""
        self.assertTrue(_buscar(""))

    def test_lo_que_no_existe_no_aparece(self):
        """Una búsqueda insensible a tildes no puede volverse insensible a todo."""
        self.assertEqual(_buscar("zzzznoexiste"), ())

    def test_respeta_el_limite(self):
        self.assertLessEqual(len(enlaces("Proceso", "", "name", 0, 3, None)), 3)

    # ------------------------------------------------------------------
    # Los filtros del desplegable (`set_query`, `link_filters`) se aplican. Sin esto,
    # el campo «sede» de una unidad ofrecía las 64 unidades en vez de las 3 sedes.
    def test_aplica_filtros_en_diccionario(self):
        filas = enlaces("Proceso", f"gestion{self.sufijo}", "name", 0, 20, {"name": "NO-EXISTE"})
        self.assertEqual(filas, ())
        filas = enlaces("Proceso", f"gestion{self.sufijo}", "name", 0, 20, {"name": self.proceso.name})
        self.assertEqual(self._codigos(filas), [self.proceso.name])

    def test_aplica_filtros_en_lista(self):
        filas = enlaces(
            "Proceso", f"gestion{self.sufijo}", "name", 0, 20, [["Proceso", "name", "!=", self.proceso.name]]
        )
        self.assertNotIn(self.proceso.name, self._codigos(filas))

    def test_filtro_like_no_rompe_los_parametros(self):
        """Un `%` del filtro no puede confundirse con los parámetros `%(txt)s`."""
        filas = enlaces(
            "Proceso", f"gestion{self.sufijo}", "name", 0, 20, {"proceso": ["like", f"%{self.sufijo}%"]}
        )
        self.assertIn(self.proceso.name, self._codigos(filas))

    def test_filtros_en_texto_json(self):
        """El navegador manda los filtros como texto JSON."""
        filas = enlaces("Proceso", f"gestion{self.sufijo}", "name", 0, 20, '{"name": "NO-EXISTE"}')
        self.assertEqual(filas, ())

    def test_devuelve_diccionarios_si_se_piden(self):
        """El diálogo «Obtener de…» (MultiSelectDialog) pide `as_dict` y lee `name`."""
        filas = enlaces("Proceso", f"gestion{self.sufijo}", "name", 0, 20, None, as_dict=1)
        self.assertEqual([f["name"] for f in filas], [self.proceso.name])
