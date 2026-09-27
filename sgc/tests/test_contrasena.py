# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Contraseña con elementos seguros (B4): letras, números, mayúsculas y minúsculas.

  La regla     — qué le falta a cada contraseña, y que se apaga por sitio
  Formulario   — fijar una contraseña débil desde el usuario se rechaza
  Restablecer  — `update_password` y el medidor de pantalla aplican la regla
"""

import frappe
from frappe.tests import IntegrationTestCase

from sgc import contrasena

FUERTE = "Cq8vT2mLr9xZ"  # clases completas y entropía alta: pasa las dos reglas
CORREO = "contrasena@sgc-prueba-pwd.example.com"


class IntegrationTestContrasena(IntegrationTestCase):
    def setUp(self):
        frappe.db.set_single_value("System Settings", "enable_password_policy", 1)
        self._conf_previa = frappe.conf.get("sgc_contrasena_clases")
        self.addCleanup(self._restaurar_conf)

    def _restaurar_conf(self):
        if self._conf_previa is None:
            frappe.conf.pop("sgc_contrasena_clases", None)
        else:
            frappe.conf.sgc_contrasena_clases = self._conf_previa

    def test_lo_que_le_falta_a_cada_contrasena(self):
        casos = {
            "Password1": [],
            "password1": ["una mayúscula"],
            "PASSWORD1": ["una minúscula"],
            "Password": ["un número"],
            "Pa1": ["al menos 8 caracteres"],
            "Ñandú2026": [],
        }
        for clave, esperado in casos.items():
            with self.subTest(clave=clave):
                self.assertEqual(contrasena.faltas(clave), esperado)

    def test_se_apaga_por_sitio(self):
        frappe.conf.sgc_contrasena_clases = 0
        contrasena.validar("solominusculas")  # no lanza
        frappe.conf.sgc_contrasena_clases = 1
        with self.assertRaises(frappe.ValidationError):
            contrasena.validar("solominusculas")

    def test_el_formulario_rechaza_una_contrasena_debil(self):
        u = frappe.get_doc({"doctype": "User", "email": CORREO, "first_name": "Prueba", "send_welcome_email": 0,
                            "new_password": "solominusculas2026"})
        with self.assertRaises(frappe.ValidationError):
            u.insert(ignore_permissions=True)

    def test_el_formulario_acepta_una_contrasena_segura(self):
        u = frappe.get_doc({"doctype": "User", "email": CORREO, "first_name": "Prueba", "send_welcome_email": 0,
                            "new_password": FUERTE}).insert(ignore_permissions=True)
        self.assertTrue(frappe.db.exists("User", u.name))

    def test_restablecer_aplica_la_regla(self):
        mapa = frappe.get_hooks("override_whitelisted_methods")
        self.assertIn("sgc.contrasena.update_password", mapa["frappe.core.doctype.user.user.update_password"])
        with self.assertRaises(frappe.ValidationError):
            contrasena.update_password("solominusculas2026", key="clave-inexistente")

    def test_el_medidor_avisa_de_las_clases(self):
        r = contrasena.test_password_strength("correcthorsebatterystaple99")
        self.assertFalse(r["feedback"]["password_policy_validation_passed"])
        self.assertIn("mayúscula", r["feedback"]["warning"])
        r = contrasena.test_password_strength(FUERTE)
        self.assertTrue(r["feedback"]["password_policy_validation_passed"])
