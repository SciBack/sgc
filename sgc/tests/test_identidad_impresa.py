# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de la identidad en los documentos impresos (#73).

#40 sacó el branding del Desk a `site_config`. Lo que quedó dentro del código
fue lo que se **imprime**: el membrete y el pie de los Print Format llevaban
`/files/membrete-upeu.png` y «UNIVERSIDAD PERUANA UNIÓN» escritos a mano, y dos
generadores de informe caían a un literal «Universidad Peruana Unión» cuando no
encontraban el dato. Cualquier instalación del producto imprimía así.

Lo que se protege aquí es el caso que nadie ve hasta que hay un segundo cliente:
**una instancia que no declara su identidad no debe imprimir la de otra**. Es
preferible un documento sin nombre a uno con el nombre equivocado — un PDF se
entrega, se archiva y se firma.

Los marcadores se resuelven al CREAR el Print Format, no al imprimir, así que
estos tests ejercitan `resolver_identidad` y los pasos que la llaman.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f3b_branding

MARCADORES = ("%%SGC_LOGO_IMG%%", "%%SGC_INSTITUCION%%", "%%SGC_PIE_INSTITUCION%%")

PLANTILLA = (
    '<div class="membrete">%%SGC_LOGO_IMG%%'
    "<b>%%SGC_INSTITUCION%%</b></div>"
    "<div class=pie>Generado por el SGC ·%%SGC_PIE_INSTITUCION%% hoy</div>"
)


class IntegrationTestIdentidadImpresa(IntegrationTestCase):
    def setUp(self):
        self._conf_original = dict(frappe.conf or {})

    def tearDown(self):
        frappe.conf.update(self._conf_original)
        for clave in ("sgc_institucion", "sgc_logo"):
            if clave not in self._conf_original:
                frappe.conf.pop(clave, None)

    # --- helper ------------------------------------------------------------

    def _declarar(self, institucion=None, logo=None):
        frappe.conf["sgc_institucion"] = institucion
        frappe.conf["sgc_logo"] = logo

    # --- el caso que importa: instancia sin declarar -----------------------

    def test_sin_identidad_declarada_no_aparece_ninguna_institucion(self):
        self._declarar(institucion=None, logo=None)

        html = f3b_branding.resolver_identidad(PLANTILLA)

        self.assertNotIn("UNIVERSIDAD", html.upper())
        self.assertNotIn("<img", html, "sin logo declarado no debe quedar un <img> roto")

    def test_sin_identidad_el_pie_no_deja_un_separador_suelto(self):
        # Detalle de acabado, pero es lo que se ve impreso: «Generado por el SGC · ·  hoy»
        # delata que falta un dato. Sin institución, el separador no debe salir.
        self._declarar(institucion=None, logo=None)

        html = f3b_branding.resolver_identidad(PLANTILLA)

        self.assertNotIn("· ·", html)
        self.assertIn("Generado por el SGC · hoy", html)

    # --- con identidad declarada -------------------------------------------

    def test_con_identidad_declarada_aparece_la_suya(self):
        self._declarar(institucion="UNIVERSIDAD DE PRUEBA", logo="/files/escudo.png")

        html = f3b_branding.resolver_identidad(PLANTILLA)

        self.assertIn("UNIVERSIDAD DE PRUEBA", html)
        self.assertIn('<img src="/files/escudo.png"', html)

    def test_no_queda_ningun_marcador_sin_resolver(self):
        # Un marcador que sobreviva se imprime tal cual en el PDF.
        self._declarar(institucion="UNIVERSIDAD DE PRUEBA", logo="/files/escudo.png")

        html = f3b_branding.resolver_identidad(PLANTILLA)

        for marcador in MARCADORES:
            self.assertNotIn(marcador, html)

    def test_tampoco_quedan_marcadores_cuando_no_hay_identidad(self):
        self._declarar(institucion=None, logo=None)

        html = f3b_branding.resolver_identidad(PLANTILLA)

        for marcador in MARCADORES:
            self.assertNotIn(marcador, html)

    def test_escapa_el_nombre_declarado(self):
        """`site_config` lo edita una persona: una comilla no debe romper el PDF."""
        self._declarar(institucion='Universidad "X" & Cía', logo=None)

        html = f3b_branding.resolver_identidad(PLANTILLA)

        self.assertNotIn('<b>Universidad "X"', html)
        self.assertIn("&amp;", html)

    # --- el nombre para los generadores de informe -------------------------

    def test_nombre_institucion_sin_declarar_devuelve_vacio(self):
        """Antes caía a un literal con el nombre de una universidad concreta."""
        frappe.conf["sgc_institucion"] = None
        anterior = frappe.db.get_default("company")
        try:
            frappe.db.set_default("company", "")
            nombre = f3b_branding.nombre_institucion()
            self.assertNotIn("Peruana", nombre or "")
        finally:
            if anterior:
                frappe.db.set_default("company", anterior)

    def test_nombre_institucion_prefiere_lo_declarado(self):
        frappe.conf["sgc_institucion"] = "UNIVERSIDAD DE PRUEBA"

        self.assertEqual(f3b_branding.nombre_institucion(), "UNIVERSIDAD DE PRUEBA")

    # --- los Print Format reales no llevan identidad dentro ----------------

    def test_el_html_del_modulo_no_nombra_a_ninguna_institucion(self):
        """El código fuente es lo que se vende: ahí no puede haber un cliente."""
        from sgc.setup import f3_informe, f6_informe_cbc, f19_ficha_pdf

        for modulo in (f19_ficha_pdf, f6_informe_cbc, f3_informe):
            for atributo in ("HTML", "HTML_PUBLICO"):
                html = getattr(modulo, atributo, None)
                if not html:
                    continue
                self.assertNotIn("UNIVERSIDAD PERUANA", html.upper(), f"{modulo.__name__}.{atributo}")
                self.assertNotIn("membrete-upeu", html, f"{modulo.__name__}.{atributo}")
