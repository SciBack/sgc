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
        self.proceso = frappe.get_doc({
            "doctype": "Proceso",
            "codigo": f"BUS-{frappe.generate_hash(length=5)}",
            "proceso": "Gestión tecnológica de prueba",
        }).insert(ignore_permissions=True)

    def _codigos(self, filas):
        return [f[0] for f in filas]

    # ------------------------------------------------------------------
    def test_encuentra_sin_tilde(self):
        """El caso que motivó todo esto."""
        self.assertIn(self.proceso.name, self._codigos(_buscar("gestion")))

    def test_encuentra_con_tilde(self):
        """Y quien la escribe bien no queda peor que quien no."""
        self.assertIn(self.proceso.name, self._codigos(_buscar("gestión")))

    def test_encuentra_a_mitad_de_palabra(self):
        """«tecnolog» corta «tecnológica» justo en la tilde."""
        self.assertIn(self.proceso.name, self._codigos(_buscar("tecnolog")))

    def test_ignora_mayusculas(self):
        self.assertIn(self.proceso.name, self._codigos(_buscar("GESTION")))

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
