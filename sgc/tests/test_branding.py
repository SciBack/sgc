# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.setup.f3b_branding` — identidad visual parametrizable.

Cubre que `run()`:
- Sin declaración en `site_config`, aplica los valores NEUTROS del producto y no
  deja el logotipo de ninguna institución.
- Con declaración, aplica exactamente lo declarado.
- Compone el `brand_html` con logotipo cuando lo hay y solo con el nombre cuando
  no, y **escapa** el nombre (llega de configuración de despliegue: una comilla
  suelta no puede romper la cabecera del sistema).
- Fija `disable_signup=1` siempre, se declare lo que se declare: es política del
  producto, no identidad de la institución.
- Es idempotente.

Gotcha (mismo patrón que f7/f11/f15): `run()` deja `frappe.flags.in_patch = True`
sin resetear. Aquí no molesta porque no se transiciona ningún documento, pero el
tearDown lo apaga para no contaminar a los tests que corran después en el mismo
proceso.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f3b_branding

CLAVES = ("sgc_app_name", "sgc_logo", "sgc_favicon", "sgc_copyright")


class IntegrationTestBranding(IntegrationTestCase):
    def setUp(self):
        # frappe.conf es el site_config cargado; se manipula en memoria para no
        # escribir en el fichero del site durante los tests.
        self._conf_original = {k: frappe.conf.get(k) for k in CLAVES}
        self._limpiar_conf()

    def tearDown(self):
        self._limpiar_conf()
        for k, v in self._conf_original.items():
            if v is not None:
                frappe.conf[k] = v
        frappe.flags.in_patch = False

    def _limpiar_conf(self):
        for k in CLAVES:
            frappe.conf.pop(k, None)

    def _ws(self):
        return frappe.get_doc("Website Settings")

    # --- sin declaración: neutro -------------------------------------------

    def test_sin_configuracion_aplica_nombre_neutro(self):
        f3b_branding.run()
        self.assertEqual(self._ws().app_name, f3b_branding.NEUTRO_APP_NAME)

    def test_sin_configuracion_no_deja_logotipo(self):
        f3b_branding.run()
        ws = self._ws()
        self.assertFalse(ws.app_logo, "sin declarar, no debe quedar ningún logotipo")

    def test_sin_configuracion_el_brand_html_es_solo_el_nombre(self):
        f3b_branding.run()
        self.assertEqual(self._ws().brand_html, f3b_branding.NEUTRO_APP_NAME)
        self.assertNotIn("<img", self._ws().brand_html)

    # --- con declaración ----------------------------------------------------

    def test_con_configuracion_aplica_lo_declarado(self):
        frappe.conf["sgc_app_name"] = "SGC Institución X"
        frappe.conf["sgc_logo"] = "/files/logo-x.png"
        frappe.conf["sgc_copyright"] = "Institución X"
        f3b_branding.run()
        ws = self._ws()
        self.assertEqual(ws.app_name, "SGC Institución X")
        self.assertEqual(ws.app_logo, "/files/logo-x.png")
        self.assertEqual(ws.copyright, "Institución X")

    def test_con_logotipo_el_brand_html_lo_incluye(self):
        frappe.conf["sgc_app_name"] = "SGC Y"
        frappe.conf["sgc_logo"] = "/files/logo-y.png"
        f3b_branding.run()
        html = self._ws().brand_html
        self.assertIn("<img", html)
        self.assertIn("/files/logo-y.png", html)
        self.assertIn("SGC Y", html)

    def test_el_nombre_se_escapa_en_el_html(self):
        """Un nombre con comillas no puede romper la cabecera del sistema."""
        frappe.conf["sgc_app_name"] = 'SGC "X" & Cía'
        frappe.conf["sgc_logo"] = "/files/logo.png"
        f3b_branding.run()
        html = self._ws().brand_html
        self.assertNotIn('"X"', html, "las comillas deben quedar escapadas")
        self.assertIn("&amp;", html)

    # --- política del producto ---------------------------------------------

    def test_disable_signup_siempre_activo(self):
        frappe.conf["sgc_app_name"] = "SGC Z"
        f3b_branding.run()
        self.assertEqual(self._ws().disable_signup, 1)

    def test_disable_signup_activo_tambien_sin_configuracion(self):
        f3b_branding.run()
        self.assertEqual(self._ws().disable_signup, 1)

    # --- idempotencia -------------------------------------------------------

    def test_reejecutar_no_cambia_el_resultado(self):
        frappe.conf["sgc_app_name"] = "SGC Repetido"
        frappe.conf["sgc_logo"] = "/files/r.png"
        f3b_branding.run()
        primero = (self._ws().app_name, self._ws().app_logo, self._ws().brand_html)
        f3b_branding.run()
        segundo = (self._ws().app_name, self._ws().app_logo, self._ws().brand_html)
        self.assertEqual(primero, segundo)

    # --- helpers puros ------------------------------------------------------

    def test_config_recorta_espacios_y_trata_vacio_como_ausente(self):
        frappe.conf["sgc_app_name"] = "  SGC W  "
        frappe.conf["sgc_logo"] = "   "
        cfg = f3b_branding._config()
        self.assertEqual(cfg["app_name"], "SGC W")
        self.assertIsNone(cfg["logo"], "una cadena en blanco es 'sin logotipo', no una ruta")
