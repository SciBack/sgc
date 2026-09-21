# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.setup.f3b_rbac._ensure_roles` — reconciliación del catálogo (#57).

Lo que se protege aquí no es un atributo cosmético. En Frappe v16 el tipo de
usuario se deriva de sus roles: si el catálogo declara un rol con `desk_access=1`
y la base lo tiene en 0, quien solo tenga ese rol pasa a `Website User` y deja de
poder entrar al Desk — sin error, sin aviso y sin traza. Ocurrió el 20-sep-2026
con cuatro cuentas de la DPGC, y la causa fue que `_ensure_roles()` saltaba los
roles ya existentes en vez de reconciliarlos.

Se cubre además que la reparación alcance a las personas, no solo a la
definición: `Role.on_update` reevalúa el `user_type` de los usuarios con ese rol
(`frappe/core/doctype/role/role.py:66-88`), y eso solo ocurre si el rol se guarda
con `save()`. Un `db.set_value` dejaría la definición correcta y a la gente
fuera, que es exactamente el fallo que este issue cierra.

Gotcha (mismo patrón que f3b_branding): `f3b_rbac.run()` manipula
`frappe.flags.in_patch`; aquí se ejercita solo `_ensure_roles()`, pero el
tearDown lo apaga por si algún test futuro llama a `run()` completo.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f3b_rbac

# Rol del catálogo declarado CON acceso al Desk: es el que protagonizó el
# incidente, y el que deja a alguien fuera si la base dice lo contrario.
ROL_CON_DESK = "Decano/Director (lectura)"
# Rol del catálogo declarado SIN acceso al Desk (evaluador externo).
ROL_SIN_DESK = "Lector Externo"
# Rol que NO está en el catálogo: el paso no debe tocarlo.
ROL_AJENO = "_SGC Rol Ajeno Al Catalogo"


class IntegrationTestRbacRoles(IntegrationTestCase):
    def setUp(self):
        self._declarado = dict(f3b_rbac.ROLES)
        # El catálogo debe existir antes de poder divergir de él.
        f3b_rbac._ensure_roles()

    def tearDown(self):
        if frappe.db.exists("Role", ROL_AJENO):
            frappe.delete_doc("Role", ROL_AJENO, force=True, ignore_permissions=True)
        # Dejar el catálogo alineado para no contaminar tests posteriores.
        f3b_rbac._ensure_roles()
        frappe.flags.in_patch = False
        frappe.db.commit()

    # --- helpers -----------------------------------------------------------

    def _desk_access(self, role_name):
        return int(frappe.db.get_value("Role", role_name, "desk_access") or 0)

    def _divergir(self, role_name):
        """Deja el rol en la base con el desk_access invertido respecto al catálogo.

        Se escribe con `db.set_value` a propósito: reproduce la divergencia tal y
        como aparece en una instancia real (alguien la tocó por fuera), sin
        disparar el `on_update` que la corregiría.
        """
        invertido = 0 if self._declarado[role_name] else 1
        frappe.db.set_value("Role", role_name, "desk_access", invertido)
        frappe.db.commit()
        self.assertEqual(self._desk_access(role_name), invertido, "la divergencia no se preparó")

    # --- criterio 1 y 2: reconcilia y lo dice ------------------------------

    def test_reconcilia_desk_access_divergente(self):
        self._divergir(ROL_CON_DESK)

        f3b_rbac._ensure_roles()

        self.assertEqual(
            self._desk_access(ROL_CON_DESK),
            self._declarado[ROL_CON_DESK],
            "el rol existente debe quedar alineado con el catálogo",
        )

    def test_reconcilia_tambien_el_rol_declarado_sin_desk(self):
        # La reconciliación va en ambos sentidos: dar acceso de más es tan
        # divergente como darlo de menos.
        self._divergir(ROL_SIN_DESK)

        f3b_rbac._ensure_roles()

        self.assertEqual(self._desk_access(ROL_SIN_DESK), 0)

    def test_informa_del_rol_y_de_los_valores(self):
        self._divergir(ROL_CON_DESK)

        _, reconciliados = f3b_rbac._ensure_roles()

        cambios = dict(reconciliados)
        self.assertIn(ROL_CON_DESK, cambios, "el rol corregido debe aparecer nombrado")
        antes, despues = cambios[ROL_CON_DESK]["desk_access"]
        self.assertEqual((antes, despues), (0, 1), "debe informar del valor anterior y el nuevo")

    # --- criterio 3 y 5: idempotencia --------------------------------------

    def test_rol_que_ya_coincide_no_se_reporta(self):
        _, reconciliados = f3b_rbac._ensure_roles()

        self.assertEqual(reconciliados, [], "sin divergencia no debe reportarse ningún cambio")

    def test_segunda_corrida_no_reporta_cambios(self):
        self._divergir(ROL_CON_DESK)

        _, primera = f3b_rbac._ensure_roles()
        _, segunda = f3b_rbac._ensure_roles()

        self.assertTrue(primera, "la primera corrida debía corregir algo")
        self.assertEqual(segunda, [], "la segunda no debe volver a tocar nada")

    def test_rol_que_ya_coincide_no_cambia_su_modified(self):
        # Idempotencia de verdad: no basta con no reportarlo, no debe escribirse.
        antes = frappe.db.get_value("Role", ROL_CON_DESK, "modified")

        f3b_rbac._ensure_roles()

        self.assertEqual(
            frappe.db.get_value("Role", ROL_CON_DESK, "modified"),
            antes,
            "un rol alineado no debe reescribirse",
        )

    # --- criterio 4: no tocar lo ajeno -------------------------------------

    def test_rol_fuera_del_catalogo_queda_intacto(self):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": ROL_AJENO,
            "desk_access": 0,
            "is_custom": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

        _, reconciliados = f3b_rbac._ensure_roles()

        self.assertEqual(self._desk_access(ROL_AJENO), 0, "no es asunto de este paso")
        self.assertNotIn(ROL_AJENO, dict(reconciliados))

    # --- lo que de verdad cerró el incidente -------------------------------

    def test_la_reconciliacion_devuelve_el_acceso_al_usuario_degradado(self):
        """El fix debe reparar a las personas, no solo a la definición.

        Es la prueba que distingue `save()` de `db.set_value`: con escritura
        directa el rol quedaría bien y el usuario seguiría siendo Website User,
        es decir, seguiría sin poder entrar.
        """
        self._divergir(ROL_CON_DESK)

        email = "sgc-test-degradado@example.com"
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        usuario = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": "Degradado",
            "roles": [{"role": ROL_CON_DESK}],
        }).insert(ignore_permissions=True)
        self.addCleanup(
            frappe.delete_doc, "User", email, force=True, ignore_permissions=True
        )
        # Con el rol sin desk_access, Frappe lo deja fuera del Desk.
        self.assertEqual(
            frappe.db.get_value("User", email, "user_type"),
            "Website User",
            "precondición: el usuario debe estar degradado antes del fix",
        )

        f3b_rbac._ensure_roles()

        usuario.reload()
        self.assertEqual(
            frappe.db.get_value("User", email, "user_type"),
            "System User",
            "al reconciliar el rol, Frappe debe devolver el acceso al usuario",
        )
