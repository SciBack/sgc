# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de la puerta única de creación de roles (#71).

Hasta este issue había DOS funciones que creaban `Role`: `f3b_rbac._ensure_roles()`,
que lee el catálogo, y `f2_workflow._ensure_role()`, que hardcodeaba `desk_access: 1`
y omitía `is_custom`. Como `f2_workflow` corre ANTES en `f_deploy_run_all`, se
adelantaba al catálogo: en un sitio limpio, 6 de los 13 roles nacían divergentes y
`_ensure_roles` los reconciliaba después (eso es lo que destapó el CI de la PR #70).

El fix de #57 tapaba el síntoma. Lo que se protege aquí es la causa: **quién decide
el `desk_access` de un rol**. La respuesta debe ser el catálogo, y no el orden en el
que se ejecuten los pasos del arranque.

Los roles de prueba se inyectan en el catálogo en vez de usar los reales: borrar un
rol real para volver a crearlo arrastraría sus `Custom DocPerm` y probaría otra cosa.
"""
import contextlib
import io

import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f2_workflow, f3b_rbac

# Roles ficticios que se añaden al catálogo durante el test. El que importa es el
# declarado SIN acceso al Desk: es el que antes de #71 nacía con 1 por la vía de
# f2_workflow, justo al revés de lo declarado.
ROL_CAT_SIN_DESK = "_SGC Test Catalogo Sin Desk"
ROL_CAT_CON_DESK = "_SGC Test Catalogo Con Desk"
# Rol que NO está en el catálogo: se crea igual, pero avisando.
ROL_NO_CATALOGADO = "_SGC Test Fuera De Catalogo"

TODOS = (ROL_CAT_SIN_DESK, ROL_CAT_CON_DESK, ROL_NO_CATALOGADO)


class IntegrationTestRolesCreacionUnica(IntegrationTestCase):
    def setUp(self):
        self._roles_original = list(f3b_rbac.ROLES)
        f3b_rbac.ROLES = [
            *self._roles_original,
            (ROL_CAT_SIN_DESK, 0),
            (ROL_CAT_CON_DESK, 1),
        ]
        self._borrar_roles_de_prueba()

    def tearDown(self):
        f3b_rbac.ROLES = self._roles_original
        self._borrar_roles_de_prueba()
        frappe.flags.in_patch = False
        frappe.db.commit()

    # --- helpers -----------------------------------------------------------

    def _borrar_roles_de_prueba(self):
        for nombre in TODOS:
            if frappe.db.exists("Role", nombre):
                frappe.delete_doc("Role", nombre, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _rol(self, nombre):
        return frappe.db.get_value(
            "Role", nombre, ["desk_access", "is_custom"], as_dict=True
        )

    # --- criterio 1: la vía de f2_workflow respeta el catálogo -------------

    def test_crear_por_la_via_de_f2_respeta_el_desk_access_declarado(self):
        """El caso que fallaba: declarado 0, creado 1.

        Antes de #71 esta llamada insertaba el rol con `desk_access: 1`
        hardcodeado. Como `desk_access` deriva el `user_type`, dar acceso de más
        es tan divergente como darlo de menos.
        """
        f2_workflow._ensure_role(ROL_CAT_SIN_DESK)

        self.assertEqual(
            self._rol(ROL_CAT_SIN_DESK).desk_access,
            0,
            "debe nacer con el desk_access del catálogo, no con el hardcodeado",
        )

    def test_crear_por_la_via_de_f2_tambien_respeta_el_declarado_con_desk(self):
        f2_workflow._ensure_role(ROL_CAT_CON_DESK)

        self.assertEqual(self._rol(ROL_CAT_CON_DESK).desk_access, 1)

    def test_el_rol_creado_queda_marcado_como_custom(self):
        # La otra mitad de la deriva: f2_workflow omitía `is_custom`, así que los
        # roles nacían con 0 y `_ensure_roles` los reconciliaba a 1 después.
        f2_workflow._ensure_role(ROL_CAT_CON_DESK)

        self.assertEqual(self._rol(ROL_CAT_CON_DESK).is_custom, 1)

    # --- criterio 3: un rol fuera del catálogo no pasa en silencio ---------

    def test_rol_fuera_del_catalogo_se_crea_pero_avisa(self):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            f2_workflow._ensure_role(ROL_NO_CATALOGADO)

        self.assertTrue(
            frappe.db.exists("Role", ROL_NO_CATALOGADO),
            "no debe romper el arranque: el rol se crea igual",
        )
        self.assertIn(
            ROL_NO_CATALOGADO,
            salida.getvalue(),
            "el aviso debe nombrar el rol, o la deriva vuelve a ser invisible",
        )

    def test_rol_del_catalogo_no_genera_aviso(self):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            f2_workflow._ensure_role(ROL_CAT_CON_DESK)

        self.assertNotIn("AVISO", salida.getvalue())

    # --- criterio 4: idempotencia ------------------------------------------

    def test_segunda_llamada_no_reescribe_el_rol(self):
        f2_workflow._ensure_role(ROL_CAT_CON_DESK)
        antes = frappe.db.get_value("Role", ROL_CAT_CON_DESK, "modified")

        f2_workflow._ensure_role(ROL_CAT_CON_DESK)

        self.assertEqual(
            frappe.db.get_value("Role", ROL_CAT_CON_DESK, "modified"),
            antes,
            "un rol existente no se toca",
        )

    def test_no_pisa_el_desk_access_de_un_rol_que_ya_existe(self):
        """`_ensure_role` crea, no reconcilia: reconciliar es de `_ensure_roles`.

        Importa que siga siendo así, porque estos módulos corren antes y no
        tienen la foto completa del catálogo ni informan de lo que cambian.
        """
        frappe.get_doc({
            "doctype": "Role",
            "role_name": ROL_CAT_CON_DESK,
            "desk_access": 0,
            "is_custom": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

        f2_workflow._ensure_role(ROL_CAT_CON_DESK)

        self.assertEqual(self._rol(ROL_CAT_CON_DESK).desk_access, 0)

    # --- el criterio que cierra el issue -----------------------------------

    def test_lo_creado_por_f2_no_deja_nada_que_reconciliar(self):
        """La prueba de que la causa está cerrada, no compensada.

        Reproduce el orden real del arranque: `f2_workflow` crea los roles y
        después `f3b_rbac` pasa por ellos. Antes de #71, esa segunda pasada los
        reportaba como reconciliados (era el «6 de 13» del CI). Ahora no debe
        tener nada que corregir.
        """
        f2_workflow._ensure_role(ROL_CAT_SIN_DESK)
        f2_workflow._ensure_role(ROL_CAT_CON_DESK)

        _, reconciliados = f3b_rbac._ensure_roles()

        tocados = dict(reconciliados)
        self.assertNotIn(ROL_CAT_SIN_DESK, tocados)
        self.assertNotIn(ROL_CAT_CON_DESK, tocados)
