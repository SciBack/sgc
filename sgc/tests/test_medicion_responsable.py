# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Quien recibe el aviso de medir un indicador puede registrar la medición (recorrido 14-oct-2026)."""

import frappe
from frappe.tests import IntegrationTestCase

from sgc.tests import factories


def _usuario(nombre, rol="Dueño de Proceso"):
    email = f"{nombre}@example.com"
    if not frappe.db.exists("User", email):
        frappe.get_doc({"doctype": "User", "email": email, "first_name": nombre, "send_welcome_email": 0,
                        "roles": [{"role": rol}]}).insert(ignore_permissions=True)
    return email


class IntegrationTestMedicionResponsable(IntegrationTestCase):
    def setUp(self):
        self.addCleanup(frappe.set_user, "Administrator")
        self.responsable = _usuario("med-responsable")
        self.otro = _usuario("med-otro")
        self.indicador = factories.crear_indicador(categoria="Proceso").name
        frappe.get_doc({"doctype": "Ficha Indicador", "indicador": self.indicador,
                        "responsable": self.responsable}).insert(ignore_permissions=True)

    def _medir(self, usuario):
        frappe.set_user(usuario)
        return frappe.get_doc({"doctype": "Valor Indicador", "indicador": self.indicador, "valor_num": 80}).insert()

    def test_el_responsable_de_la_ficha_registra(self):
        self.assertTrue(self._medir(self.responsable).name)

    def test_otro_dueno_de_proceso_no_registra(self):
        with self.assertRaises(frappe.PermissionError):
            self._medir(self.otro)

    def test_la_dpgc_registra_cualquiera(self):
        self.assertTrue(self._medir(_usuario("med-dpgc", "DPGC")).name)
