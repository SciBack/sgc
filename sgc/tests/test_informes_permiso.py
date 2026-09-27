# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Los informes del SGC los puede ejecutar quien lee sus datos, no solo System Manager.

Frappe exige el permiso «report» sobre el `ref_doctype` para EJECUTAR un Script
Report (`frappe/desk/query_report.py:263`), aunque el informe no tenga roles
propios. La matriz RBAC nunca lo daba, así que hasta el 27-sep-2026 los seis
informes del SGC fallaban con PermissionError para la DPGC y para cualquier rol
que no fuera System Manager. Nadie lo vio porque se probaron como administrador.

Por eso este test **ejecuta** cada informe como un usuario con UN solo rol de
lectura, en vez de preguntar a `has_permission`.

Depende de que el RBAC (`f3b_rbac`) esté aplicado en el sitio, como en el CI y en
producción (corre en `after_migrate`).
"""

import frappe
from frappe.desk.query_report import run
from frappe.tests import IntegrationTestCase

from sgc.setup.f3b_rbac import doctypes_con_informe

USUARIO = "sgc-prueba-informes-dpgc@example.com"
ROL = "DPGC"


class IntegrationTestInformesPermiso(IntegrationTestCase):
    def setUp(self):
        if not frappe.db.exists("User", USUARIO):
            u = frappe.get_doc({"doctype": "User", "email": USUARIO, "first_name": "informes",
                                "send_welcome_email": 0})
            u.append("roles", {"role": ROL})
            u.insert(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user("Administrator")

    def _informes(self):
        modulos = frappe.get_all("Module Def", filters={"app_name": "sgc"}, pluck="name")
        return frappe.get_all(
            "Report",
            filters={"is_standard": "Yes", "module": ["in", modulos], "disabled": 0,
                     "report_type": "Script Report"},
            fields=["name", "ref_doctype"],
        )

    def test_hay_informes_y_todos_tienen_permiso_report_para_la_dpgc(self):
        informes = self._informes()
        self.assertGreaterEqual(len(informes), 6)
        self.assertEqual({i.ref_doctype for i in informes} - doctypes_con_informe(), set())
        for i in informes:
            self.assertEqual(
                frappe.db.get_value("Custom DocPerm",
                                    {"parent": i.ref_doctype, "role": ROL, "permlevel": 0}, "report"),
                1, f"{ROL} sin «report» en {i.ref_doctype}: no puede abrir {i.name}",
            )

    def test_la_dpgc_ejecuta_cada_informe(self):
        frappe.set_user(USUARIO)
        for i in self._informes():
            with self.subTest(informe=i.name):
                resultado = run(i.name, filters={})
                self.assertIn("result", resultado)

    def test_quien_no_lee_el_doctype_sigue_sin_poder(self):
        """El arreglo no abre nada de más: sin lectura no hay informe."""
        sin_rol = "sgc-prueba-informes-sin-rol@example.com"
        if not frappe.db.exists("User", sin_rol):
            frappe.get_doc({"doctype": "User", "email": sin_rol, "first_name": "sin rol",
                            "send_welcome_email": 0}).insert(ignore_permissions=True)
        frappe.set_user(sin_rol)
        with self.assertRaises(frappe.PermissionError):
            run("Salidas No Conformes", filters={})
