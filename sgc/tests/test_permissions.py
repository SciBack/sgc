# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Suite de integración para `sgc/permissions.py` — M07 visibilidad por programa.

Verifica el mecanismo *opt-in* de acotamiento por Programa Sede:

  - Dos usuarios "Responsable de Calidad de Programa", cada uno con una User
    Permission de un Programa Sede distinto (A y B), quedan AISLADOS: A no ve la
    Autoevaluacion / Valoracion / Plan del programa B, ni viceversa.
  - Un usuario DPGC (rol exento, SIN User Permission) ve AMBOS programas.
  - Un usuario con rol acotado pero SIN User Permission de Programa Sede ve TODO
    (opt-in: el mecanismo está inactivo hasta que se siembra la User Permission).
  - Los registros sin programa (Autoevaluacion institucional) son visibles a
    todos (no atribuibles a un programa => compartidos).

Cada test corre en su propia transacción (rollback automático de
`IntegrationTestCase`); no se hace commit, así que ni usuarios ni User Permission
ni DocPerm de prueba persisten.

Convenciones:
  - `Autoevaluacion` tiene Workflow activo; se desactiva en setUp (las factories
    lo requieren para insertar sin disparar WorkflowPermissionError).
  - Se otorga lectura (DocPerm) a los roles de prueba en setUp para no depender
    del orden de ejecución de `f3b_rbac`. `permission_query_conditions` solo
    filtra a quien YA tiene acceso al DocType.
"""
import frappe
from frappe.permissions import add_permission, update_permission_property
from frappe.tests import IntegrationTestCase

from sgc import permissions
from sgc.tests import factories

# DocTypes acotados por el mecanismo (los que se les otorga lectura en el test).
DOCTYPES_ACOTADOS = [
    "Autoevaluacion",
    "Valoracion Criterio",
    "Valoracion Estandar",
    "Plan Mejora",
    "Hallazgo",
    "No Conformidad",
]

ROL_ACOTADO = "Responsable de Calidad de Programa"
ROL_EXENTO = "DPGC"


class IntegrationTestPermissions(IntegrationTestCase):

    PREFIJO = "TEST-M07"

    # ------------------------------------------------------------------ setUp
    def setUp(self):
        # Autoevaluacion, Plan Mejora y No Conformidad tienen Workflow activo en
        # prod; el setUp crea esos docs con estados directos y sin desactivar el
        # workflow el aplicado commitea y rompe el aislamiento del rollback (→
        # colisión de código entre tests).
        for dt in ("Autoevaluacion", "Plan Mejora", "No Conformidad"):
            factories.desactivar_workflow(dt)
        self._user_prev = frappe.session.user
        frappe.set_user("Administrator")

        for r in (ROL_ACOTADO, ROL_EXENTO):
            self._ensure_role(r)

        # Estructura: dos Programa Sede independientes (A y B).
        self.prog_a = self._crear_programa_sede("A")
        self.prog_b = self._crear_programa_sede("B")

        # Árbol base compartido (marco + escala NL/L/LP) — un criterio basta.
        arbol = factories.crear_marco_prueba(
            n_estandares=1, n_criterios=1, prefijo=self.PREFIJO
        )
        self.marco = arbol["marco"]
        est = arbol["estandares"][0]
        crit = arbol["criterios"][est][0]

        # Autoevaluaciones: una por programa + una institucional (sin programa).
        self.ae_a = factories.crear_autoevaluacion(
            self.marco, codigo=f"{self.PREFIJO}-AE-A", programa_sede=self.prog_a
        ).name
        self.ae_b = factories.crear_autoevaluacion(
            self.marco, codigo=f"{self.PREFIJO}-AE-B", programa_sede=self.prog_b
        ).name
        self.ae_null = factories.crear_autoevaluacion(
            self.marco, codigo=f"{self.PREFIJO}-AE-N"
        ).name  # sin programa_sede

        # Valoracion Criterio (dispara scoring -> upsert Valoracion Estandar).
        factories.valorar_criterio(self.ae_a, crit)
        factories.valorar_criterio(self.ae_b, crit)
        self.ve_a = frappe.db.get_value(
            "Valoracion Estandar", {"autoevaluacion": self.ae_a}, "name"
        )
        self.ve_b = frappe.db.get_value(
            "Valoracion Estandar", {"autoevaluacion": self.ae_b}, "name"
        )

        # Plan Mejora por programa (derivado vía su autoevaluacion).
        self.plan_a = self._crear_plan(f"{self.PREFIJO}-PLAN-A", self.ae_a)
        self.plan_b = self._crear_plan(f"{self.PREFIJO}-PLAN-B", self.ae_b)

        # Otorgar lectura a los roles de prueba (independiente de f3b_rbac).
        for dt in DOCTYPES_ACOTADOS:
            self._ensure_lectura(ROL_ACOTADO, dt)
            self._ensure_lectura(ROL_EXENTO, dt)

        # Usuarios.
        self.user_a = self._crear_usuario("resp-a", ROL_ACOTADO, self.prog_a)
        self.user_b = self._crear_usuario("resp-b", ROL_ACOTADO, self.prog_b)
        self.user_dpgc = self._crear_usuario("dpgc-x", ROL_EXENTO, None)  # exento
        # Acotado por rol pero SIN User Permission -> opt-in inactivo (ve todo).
        self.user_sin_up = self._crear_usuario("resp-libre", ROL_ACOTADO, None)

        frappe.clear_cache()

    def tearDown(self):
        frappe.set_user(self._user_prev)

    # -------------------------------------------------------------- factories
    def _ensure_role(self, role_name):
        if not frappe.db.exists("Role", role_name):
            frappe.get_doc({
                "doctype": "Role", "role_name": role_name,
                "desk_access": 1, "is_custom": 1,
            }).insert(ignore_permissions=True)

    def _ensure(self, doctype, codigo, values):
        if frappe.db.exists(doctype, codigo):
            return codigo
        doc = frappe.get_doc({"doctype": doctype, "codigo": codigo, **values})
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc.name

    def _crear_programa_sede(self, suf):
        uo = self._ensure("Unidad Organica", f"{self.PREFIJO}-UO-{suf}",
                          {"nombre": f"Sede {suf}"})
        prog = self._ensure("Programa", f"{self.PREFIJO}-PR-{suf}",
                            {"nombre": f"Programa {suf}"})
        return self._ensure("Programa Sede", f"{self.PREFIJO}-PS-{suf}",
                            {"programa": prog, "sede": uo})

    def _crear_plan(self, codigo, autoevaluacion):
        # Idempotente: el alta de usuarios en setUp commitea (side effects de
        # User), así que los fixtures no siempre revierten entre tests → reusar
        # el plan si ya existe en vez de chocar con el unique del código.
        if frappe.db.exists("Plan Mejora", codigo):
            return codigo
        doc = frappe.get_doc({
            "doctype": "Plan Mejora", "codigo": codigo, "titulo": codigo,
            "autoevaluacion": autoevaluacion,
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc.name

    def _ensure_lectura(self, role, doctype):
        add_permission(doctype, role, 0)
        update_permission_property(doctype, role, 0, "read", 1, validate=False)

    def _crear_usuario(self, local, rol, programa_sede):
        email = f"{local}@{self.PREFIJO.lower()}.test"
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.get_doc({
            "doctype": "User", "email": email, "first_name": local,
            "send_welcome_email": 0, "roles": [{"role": rol}],
        }).insert(ignore_permissions=True)
        if programa_sede:
            frappe.get_doc({
                "doctype": "User Permission", "user": email,
                "allow": "Programa Sede", "for_value": programa_sede,
            }).insert(ignore_permissions=True)
        return email

    # --------------------------------------------------------------- helpers
    def _listar(self, doctype, filtros, user):
        """Names visibles de `doctype` para `user` (aplica permission_query_conditions)."""
        frappe.set_user(user)
        try:
            return set(frappe.get_list(doctype, filters=filtros, pluck="name"))
        finally:
            frappe.set_user("Administrator")

    def _ae_visibles(self, user):
        return self._listar("Autoevaluacion", {"marco_normativo": self.marco}, user)

    # =====================================================================
    # Helper central: programas_permitidos / es_exento
    # =====================================================================
    def test_helper_usuario_acotado_devuelve_su_programa(self):
        self.assertEqual(permissions.programas_permitidos(self.user_a), [self.prog_a])
        self.assertEqual(permissions.programas_permitidos(self.user_b), [self.prog_b])

    def test_helper_exento_y_sin_user_permission_devuelven_none(self):
        # DPGC exento por rol.
        self.assertIsNone(permissions.programas_permitidos(self.user_dpgc))
        self.assertTrue(permissions.es_exento(self.user_dpgc))
        # Rol acotado pero sin User Permission -> opt-in inactivo.
        self.assertIsNone(permissions.programas_permitidos(self.user_sin_up))
        self.assertFalse(permissions.es_exento(self.user_sin_up))

    # =====================================================================
    # Aislamiento — Autoevaluacion (campo directo programa_sede)
    # =====================================================================
    def test_autoevaluacion_aislada_entre_programas(self):
        vis_a = self._ae_visibles(self.user_a)
        self.assertIn(self.ae_a, vis_a)
        self.assertNotIn(self.ae_b, vis_a)       # A no ve el programa B
        self.assertIn(self.ae_null, vis_a)       # institucional visible a todos

        vis_b = self._ae_visibles(self.user_b)
        self.assertIn(self.ae_b, vis_b)
        self.assertNotIn(self.ae_a, vis_b)       # B no ve el programa A
        self.assertIn(self.ae_null, vis_b)

    def test_autoevaluacion_dpgc_ve_ambos(self):
        vis = self._ae_visibles(self.user_dpgc)
        self.assertIn(self.ae_a, vis)
        self.assertIn(self.ae_b, vis)
        self.assertIn(self.ae_null, vis)

    def test_autoevaluacion_opt_in_sin_user_permission_ve_todo(self):
        vis = self._ae_visibles(self.user_sin_up)
        self.assertIn(self.ae_a, vis)
        self.assertIn(self.ae_b, vis)
        self.assertIn(self.ae_null, vis)

    # =====================================================================
    # Aislamiento — Valoracion Criterio (vía autoevaluacion)
    # =====================================================================
    def test_valoracion_criterio_aislada(self):
        f = {"autoevaluacion": ["in", [self.ae_a, self.ae_b]]}
        vis_a = self._listar("Valoracion Criterio", f, self.user_a)
        vc_b = frappe.db.get_value(
            "Valoracion Criterio", {"autoevaluacion": self.ae_b}, "name")
        vc_a = frappe.db.get_value(
            "Valoracion Criterio", {"autoevaluacion": self.ae_a}, "name")
        self.assertIn(vc_a, vis_a)
        self.assertNotIn(vc_b, vis_a)
        # DPGC ve ambas.
        vis_dpgc = self._listar("Valoracion Criterio", f, self.user_dpgc)
        self.assertIn(vc_a, vis_dpgc)
        self.assertIn(vc_b, vis_dpgc)

    # =====================================================================
    # Aislamiento — Valoracion Estandar (vía autoevaluacion)
    # =====================================================================
    def test_valoracion_estandar_aislada(self):
        self.assertTrue(self.ve_a and self.ve_b, "scoring debió crear las Valoracion Estandar")
        f = {"autoevaluacion": ["in", [self.ae_a, self.ae_b]]}
        vis_a = self._listar("Valoracion Estandar", f, self.user_a)
        self.assertIn(self.ve_a, vis_a)
        self.assertNotIn(self.ve_b, vis_a)
        vis_b = self._listar("Valoracion Estandar", f, self.user_b)
        self.assertIn(self.ve_b, vis_b)
        self.assertNotIn(self.ve_a, vis_b)

    # =====================================================================
    # Aislamiento — Plan Mejora (vía autoevaluacion)
    # =====================================================================
    def test_plan_mejora_aislado(self):
        f = {"name": ["in", [self.plan_a, self.plan_b]]}
        vis_a = self._listar("Plan Mejora", f, self.user_a)
        self.assertIn(self.plan_a, vis_a)
        self.assertNotIn(self.plan_b, vis_a)
        vis_dpgc = self._listar("Plan Mejora", f, self.user_dpgc)
        self.assertIn(self.plan_a, vis_dpgc)
        self.assertIn(self.plan_b, vis_dpgc)

    # =====================================================================
    # has_permission — acceso a UN documento (get_doc)
    # =====================================================================
    def test_has_permission_documento_aislado(self):
        doc_a = frappe.get_doc("Autoevaluacion", self.ae_a)
        doc_b = frappe.get_doc("Autoevaluacion", self.ae_b)
        doc_n = frappe.get_doc("Autoevaluacion", self.ae_null)
        # user_a: ve su programa y el institucional, no el ajeno.
        self.assertTrue(permissions.has_permission(doc_a, "read", self.user_a))
        self.assertFalse(permissions.has_permission(doc_b, "read", self.user_a))
        self.assertTrue(permissions.has_permission(doc_n, "read", self.user_a))
        # DPGC exento: todo.
        self.assertTrue(permissions.has_permission(doc_b, "read", self.user_dpgc))
        # Plan Mejora derivado vía autoevaluacion.
        plan_b = frappe.get_doc("Plan Mejora", self.plan_b)
        self.assertFalse(permissions.has_permission(plan_b, "read", self.user_a))
        self.assertTrue(permissions.has_permission(plan_b, "read", self.user_b))

    # =====================================================================
    # Condición SQL vacía cuando no hay restricción (contrato interno)
    # =====================================================================
    def test_pqc_devuelve_vacio_para_exentos(self):
        self.assertEqual(permissions.pqc_autoevaluacion(self.user_dpgc), "")
        self.assertEqual(permissions.pqc_plan_mejora(self.user_sin_up), "")
        # Acotado -> condición no vacía que menciona el programa.
        cond = permissions.pqc_autoevaluacion(self.user_a)
        self.assertIn("programa_sede", cond)
        self.assertIn(self.prog_a, cond)
