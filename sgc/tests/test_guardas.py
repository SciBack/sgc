# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""La guarda de sitio deja pasar el laboratorio y frena el sitio institucional.

El caso que estos tests protegen no es hipotético: los scripts E2E se corrieron
una vez contra producción y sembraron una autoevaluación completa sin marca
[DEMO], que después se reportó como avance real durante seis semanas.

Lo que importa comprobar es que la guarda falle *antes* de escribir nada, y que
el sitio del CI —`test_site.localhost`— siga pasando: una guarda que rompa la
suite se acaba desactivando, y entonces no protege de nada.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import guardas


class TestGuardaDeSitio(IntegrationTestCase):
    def test_sitio_localhost_es_de_pruebas(self):
        """La convención de bench para sitios locales basta: no hay que declarar nada."""
        self.assertTrue(guardas.sitio_es_de_pruebas("sgc.localhost"))
        self.assertTrue(guardas.sitio_es_de_pruebas("test_site.localhost"))

    def test_el_sitio_de_esta_suite_pasa(self):
        """El sitio donde corre el CI tiene que pasar, o la guarda rompe la suite."""
        self.assertTrue(guardas.sitio_es_de_pruebas())

    def test_sitio_institucional_no_es_de_pruebas(self):
        """Un dominio real no pasa por parecerse a uno de pruebas."""
        self.assertFalse(guardas.sitio_es_de_pruebas("calidad.upeu.edu.pe"))
        self.assertFalse(guardas.sitio_es_de_pruebas("staging.calidad.upeu.edu.pe"))
        self.assertFalse(guardas.sitio_es_de_pruebas("localhost.calidad.upeu.edu.pe"))

    def test_se_puede_declarar_un_sitio_explicitamente(self):
        """Habilitar un sitio institucional es posible, pero hay que escribirlo."""
        original = frappe.conf.get("sgc_sitios_e2e")
        frappe.conf["sgc_sitios_e2e"] = ["staging.ejemplo.edu.pe"]
        try:
            self.assertTrue(guardas.sitio_es_de_pruebas("staging.ejemplo.edu.pe"))
            self.assertFalse(guardas.sitio_es_de_pruebas("otro.ejemplo.edu.pe"))
        finally:
            if original is None:
                frappe.conf.pop("sgc_sitios_e2e", None)
            else:
                frappe.conf["sgc_sitios_e2e"] = original

    def test_exigir_aborta_en_sitio_institucional(self):
        """La excepción nombra el sitio y dice cómo habilitarlo, sin haber escrito nada."""
        original = frappe.local.site
        frappe.local.site = "calidad.upeu.edu.pe"
        try:
            with self.assertRaises(guardas.SitioNoEsDePruebas) as ctx:
                guardas.exigir_sitio_de_pruebas("f2_e2e_test")
        finally:
            frappe.local.site = original
        mensaje = str(ctx.exception)
        self.assertIn("calidad.upeu.edu.pe", mensaje)
        self.assertIn("sgc_sitios_e2e", mensaje)
        self.assertIn("demo_seed", mensaje)

    def test_exigir_deja_pasar_el_laboratorio(self):
        """En un sitio de pruebas no interrumpe."""
        original = frappe.local.site
        frappe.local.site = "sgc.localhost"
        try:
            guardas.exigir_sitio_de_pruebas("f2_e2e_test")
        finally:
            frappe.local.site = original
