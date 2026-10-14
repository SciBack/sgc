# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""La identidad en los documentos impresos (#73), leída al imprimir.

#40 sacó el branding del Desk a `site_config`. Lo que quedaba en el código era lo que se
**imprime**: membrete y pie con el logo y el nombre de una universidad concreta. Cualquier
instalación del producto imprimía así.

Desde la 1.2.0 los formatos son ficheros estándar comunes a todas las instituciones y leen la
identidad AL IMPRIMIR con `sgc_identidad()` (hook `jinja`, `sgc/identidad.py`). Lo que se
protege: **una instancia que no declara su identidad no imprime la de otra**, y la que la
declara imprime la suya sin desplegar nada. Es preferible un documento sin nombre a uno con el
nombre equivocado: un PDF se entrega, se archiva y se firma.
"""

import frappe
from frappe.tests import IntegrationTestCase

from sgc import estandar
from sgc.identidad import sgc_identidad
from sgc.setup import f3b_branding

PLANTILLA = (
    "{% set id = sgc_identidad() %}"
    '<div class="membrete">{% if id.logo %}<img src="{{ id.logo | e }}">{% endif %}'
    "<b>{{ id.institucion | e }}</b></div>"
)


class IntegrationTestIdentidadImpresa(IntegrationTestCase):
    def setUp(self):
        self._conf_original = dict(frappe.conf or {})

    def tearDown(self):
        frappe.conf.update(self._conf_original)
        for clave in ("sgc_institucion", "sgc_logo"):
            if clave not in self._conf_original:
                frappe.conf.pop(clave, None)

    def _declarar(self, institucion=None, logo=None):
        frappe.conf["sgc_institucion"] = institucion
        frappe.conf["sgc_logo"] = logo

    def _imprimir(self):
        return frappe.render_template(PLANTILLA, {})

    # --- el método que leen las plantillas ---------------------------------

    def test_esta_registrado_en_el_hook_jinja(self):
        self.assertIn("sgc.identidad.sgc_identidad", frappe.get_hooks("jinja")["methods"])

    def test_sin_identidad_declarada_no_aparece_ninguna_institucion(self):
        self._declarar()
        html = self._imprimir()
        self.assertNotIn("<img", html)
        self.assertEqual(sgc_identidad().institucion, "")

    def test_con_identidad_declarada_aparece_la_suya_al_imprimir(self):
        self._declarar("UNIVERSIDAD DE PRUEBA", "/files/logo-prueba.png")
        html = self._imprimir()
        self.assertIn("UNIVERSIDAD DE PRUEBA", html)
        self.assertIn('src="/files/logo-prueba.png"', html)

    def test_escapa_el_nombre_declarado(self):
        self._declarar("Universidad <b>&</b>")
        self.assertIn("&amp;", self._imprimir())

    # --- los formatos estándar no llevan identidad dentro ------------------

    def test_ningun_formato_estandar_nombra_a_una_institucion(self):
        """El código fuente es lo que se vende: ahí no puede haber un cliente."""
        for nombre, formato in estandar.formatos().items():
            with self.subTest(formato=nombre):
                html = formato.get("html") or ""
                self.assertNotIn("UNIVERSIDAD PERUANA", html.upper())
                self.assertNotIn("membrete-upeu", html)
                self.assertNotIn("%%SGC_", html, "marcador horneado: debe leerse al imprimir")

    def test_los_formatos_con_membrete_leen_la_identidad_al_imprimir(self):
        for nombre in ("Ficha de Caracterizacion", "Plan Anual de Auditoria", "Diagnostico CBC SUNEDU",
                       "Informe de Autoevaluacion SINEACE"):
            with self.subTest(formato=nombre):
                self.assertIn("sgc_identidad()", estandar.formatos()[nombre]["html"])

    # --- el nombre para los generadores de informe -------------------------

    def test_nombre_institucion_sin_declarar_devuelve_vacio(self):
        """Antes caía a un literal con el nombre de una universidad concreta."""
        frappe.conf["sgc_institucion"] = None
        anterior = frappe.db.get_default("company")
        try:
            frappe.db.set_default("company", "")
            self.assertNotIn("Peruana", f3b_branding.nombre_institucion() or "")
        finally:
            if anterior:
                frappe.db.set_default("company", anterior)

    def test_nombre_institucion_prefiere_lo_declarado(self):
        frappe.conf["sgc_institucion"] = "UNIVERSIDAD DE PRUEBA"
        self.assertEqual(f3b_branding.nombre_institucion(), "UNIVERSIDAD DE PRUEBA")
