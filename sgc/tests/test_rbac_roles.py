# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""El catálogo de roles del SGC y su reconciliación (#57), con el mecanismo nativo de Frappe.

Desde la 1.2.0 los roles son un fixture (`sgc/fixtures/role.json`). Frappe lo reimporta en cada
`migrate` con `force=True` (frappe/core/doctype/data_import/data_import.py, import_doc), así que
un `desk_access` cambiado a mano vuelve a lo declarado: es la reconciliación que antes hacía
el antiguo `f3b_rbac._ensure_roles`. Lo que se prueba aquí es que esa reimportación repara el rol Y a las
personas (el incidente del 20-sep-2026: cuatro cuentas fuera del Desk).
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.fixtures import sync_fixtures

from sgc import estandar

ROL_CON_DESK = "Dueño de Proceso"
ROL_SIN_DESK = "Lector Externo"


class IntegrationTestRbacRoles(IntegrationTestCase):
    def tearDown(self):
        # Pase lo que pase en el test, el catálogo queda como lo declara la app.
        sync_fixtures("sgc")

    def _desk_access(self, rol):
        return int(frappe.db.get_value("Role", rol, "desk_access"))

    def _divergir(self, rol):
        """Deja el rol con el desk_access invertido, como lo dejaría un cambio a mano en el Desk."""
        doc = frappe.get_doc("Role", rol)
        doc.desk_access = 0 if doc.desk_access else 1
        doc.save(ignore_permissions=True)
        frappe.db.commit()

    def test_el_catalogo_declara_cada_rol_con_su_acceso(self):
        roles = estandar.roles()
        self.assertGreaterEqual(len(roles), 14)
        self.assertEqual(int(roles[ROL_CON_DESK]["desk_access"]), 1)
        self.assertEqual(int(roles[ROL_SIN_DESK]["desk_access"]), 0)
        self.assertEqual(int(roles["Colaborador"]["desk_access"]), 1, "da el Desk para reportar eventos de riesgo")

    def test_el_sitio_tiene_los_roles_como_los_declara_la_app(self):
        for rol, declarado in estandar.roles().items():
            with self.subTest(rol=rol):
                self.assertEqual(self._desk_access(rol), int(declarado.get("desk_access") or 0))

    def test_migrar_reconcilia_un_desk_access_cambiado_a_mano(self):
        for rol in (ROL_CON_DESK, ROL_SIN_DESK):
            with self.subTest(rol=rol):
                declarado = int(estandar.roles()[rol]["desk_access"])
                self._divergir(rol)
                self.assertNotEqual(self._desk_access(rol), declarado, "precondición")

                sync_fixtures("sgc")

                self.assertEqual(self._desk_access(rol), declarado)

    def test_la_reconciliacion_devuelve_el_acceso_al_usuario_degradado(self):
        """El arreglo debe reparar a las personas, no solo a la definición del rol."""
        self._divergir(ROL_CON_DESK)
        email = "sgc-test-degradado@example.com"
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.get_doc(
            {"doctype": "User", "email": email, "first_name": "Degradado", "roles": [{"role": ROL_CON_DESK}]}
        ).insert(ignore_permissions=True)
        self.addCleanup(frappe.delete_doc, "User", email, force=True, ignore_permissions=True)
        self.assertEqual(frappe.db.get_value("User", email, "user_type"), "Website User", "precondición")

        sync_fixtures("sgc")

        self.assertEqual(frappe.db.get_value("User", email, "user_type"), "System User")
