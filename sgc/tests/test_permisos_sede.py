# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Visibilidad por sede — `sgc.permissions` con User Permission sobre la sede.

Decisión de Alberto (22-oct-2026): a quien se le asigna una sede ve solo lo de
los programas de esa sede, también si es Analista de Calidad; solo la DPGC y
System Manager ven todo. Lo que no es de ningún programa lo ve todo el mundo.

Se comprueba:

  - la sede equivale a todos sus Programa Sede, también a los creados después;
  - un Analista con sede queda acotado y uno sin sede ve todo;
  - Valor Indicador y Comite (acotados por campo directo) filtran en listas y en
    el acceso a un registro, y lo que no tiene programa sigue visible;
  - Frappe acota por sí solo la lista de Programa Sede, sin mirar la escuela;
  - una sede sin programas no rompe la consulta (un `in ()` es SQL inválido);
  - `asignar_sede` solo acepta unidades de tipo Sede y no duplica.

Cada test corre en su transacción (rollback de `IntegrationTestCase`).
"""
import frappe
from frappe.permissions import add_permission, update_permission_property
from frappe.tests import IntegrationTestCase

from sgc import permissions
from sgc.tests import factories

PREFIJO = "TSEDE"
ROL_ANALISTA = "Analista de Calidad (DPGC)"
ROL_DPGC = "DPGC"
DOCTYPES_LEIDOS = ("Valor Indicador", "Comite", "Programa Sede")


class IntegrationTestPermisosSede(IntegrationTestCase):

    def setUp(self):
        self._user_prev = frappe.session.user
        frappe.set_user("Administrator")

        self.sede_a = self._sede("A")
        self.sede_b = self._sede("B")
        self.sede_vacia = self._sede("VACIA")
        # La escuela es una unidad cualquiera: no debe contar para la sede.
        self.escuela = factories._ensure_named("Unidad Organica", f"{PREFIJO}-ESC", {
            "nombre": "Escuela de prueba", "tipo": "Escuela",
        }).name

        self.prog_a = factories.crear_programa_sede(
            f"{PREFIJO}-PS-A", prefijo=PREFIJO, sede=self.sede_a, escuela=self.escuela
        ).name
        self.prog_b = factories.crear_programa_sede(
            f"{PREFIJO}-PS-B", prefijo=PREFIJO, sede=self.sede_b
        ).name

        indicador = factories.crear_indicador(prefijo=PREFIJO)
        self.valor_a = factories.crear_valor_indicador(indicador, programa_sede=self.prog_a).name
        self.valor_b = factories.crear_valor_indicador(indicador, programa_sede=self.prog_b).name
        self.valor_sin = factories.crear_valor_indicador(indicador).name

        self.comite_a = self._comite("A", self.prog_a)
        self.comite_b = self._comite("B", self.prog_b)

        for dt in DOCTYPES_LEIDOS:
            for rol in (ROL_ANALISTA, ROL_DPGC):
                add_permission(dt, rol, 0)
                update_permission_property(dt, rol, 0, "read", 1, validate=False)

        self.analista_a = self._usuario("analista-a", ROL_ANALISTA)
        permissions.asignar_sede(self.analista_a, self.sede_a)
        self.analista_libre = self._usuario("analista-libre", ROL_ANALISTA)
        self.dpgc_con_sede = self._usuario("dpgc", ROL_DPGC)
        permissions.asignar_sede(self.dpgc_con_sede, self.sede_b)
        frappe.clear_cache()

    def tearDown(self):
        frappe.set_user(self._user_prev)

    # -------------------------------------------------------------- factories
    def _sede(self, suf):
        return factories._ensure_named("Unidad Organica", f"{PREFIJO}-SEDE-{suf}", {
            "nombre": f"Sede {suf}", "tipo": "Sede",
        }).name

    def _comite(self, suf, programa_sede):
        return factories._ensure_named("Comite", f"{PREFIJO}-COM-{suf}", {
            "nombre": f"Comité {suf}", "programa_sede": programa_sede,
        }).name

    def _usuario(self, local, rol):
        email = f"{local}@{PREFIJO.lower()}.test"
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.get_doc({
            "doctype": "User", "email": email, "first_name": local,
            "send_welcome_email": 0, "roles": [{"role": rol}],
        }).insert(ignore_permissions=True)
        return email

    def _listar(self, doctype, user, filtros=None):
        frappe.set_user(user)
        try:
            return set(frappe.get_list(doctype, filters=filtros or {}, pluck="name"))
        finally:
            frappe.set_user("Administrator")

    def _valores(self, user):
        return self._listar("Valor Indicador", user, {
            "name": ["in", [self.valor_a, self.valor_b, self.valor_sin]],
        })

    # ================================================================= tests
    def test_la_sede_equivale_a_sus_programas_tambien_los_nuevos(self):
        self.assertEqual(permissions.programas_permitidos(self.analista_a), [self.prog_a])
        nuevo = factories.crear_programa_sede(
            f"{PREFIJO}-PS-A2", prefijo=PREFIJO, sede=self.sede_a
        ).name
        self.assertEqual(permissions.programas_permitidos(self.analista_a), sorted([self.prog_a, nuevo]))

    def test_la_sede_manda_sobre_el_rol_de_analista(self):
        self.assertFalse(permissions.es_exento(self.analista_a))
        self.assertEqual(self._valores(self.analista_a), {self.valor_a, self.valor_sin})

    def test_analista_sin_sede_ve_todo(self):
        self.assertIsNone(permissions.programas_permitidos(self.analista_libre))
        self.assertEqual(self._valores(self.analista_libre), {self.valor_a, self.valor_b, self.valor_sin})

    def test_la_dpgc_ve_todo_aunque_tenga_sede(self):
        self.assertIsNone(permissions.programas_permitidos(self.dpgc_con_sede))
        self.assertEqual(self._valores(self.dpgc_con_sede), {self.valor_a, self.valor_b, self.valor_sin})

    def test_comite_acotado_por_sede(self):
        visibles = self._listar("Comite", self.analista_a, {"name": ["like", f"{PREFIJO}-%"]})
        self.assertIn(self.comite_a, visibles)
        self.assertNotIn(self.comite_b, visibles)

    def test_acceso_a_un_registro_de_otra_sede(self):
        ajeno = frappe.get_doc("Valor Indicador", self.valor_b)
        propio = frappe.get_doc("Valor Indicador", self.valor_a)
        sin_programa = frappe.get_doc("Valor Indicador", self.valor_sin)
        self.assertFalse(permissions.has_permission(ajeno, "read", self.analista_a))
        self.assertTrue(permissions.has_permission(propio, "read", self.analista_a))
        self.assertTrue(permissions.has_permission(sin_programa, "read", self.analista_a))

    def test_frappe_acota_la_lista_de_programas_sin_mirar_la_escuela(self):
        visibles = self._listar("Programa Sede", self.analista_a, {"name": ["like", f"{PREFIJO}-%"]})
        self.assertIn(self.prog_a, visibles, "la escuela del programa no debe esconderlo")
        self.assertNotIn(self.prog_b, visibles)

    def test_sede_sin_programas_solo_ve_lo_que_no_es_de_ningun_programa(self):
        user = self._usuario("analista-vacia", ROL_ANALISTA)
        permissions.asignar_sede(user, self.sede_vacia)
        self.assertEqual(permissions.programas_permitidos(user), [])
        self.assertEqual(self._valores(user), {self.valor_sin})

    def test_asignar_sede_rechaza_lo_que_no_es_sede_y_no_duplica(self):
        with self.assertRaises(frappe.ValidationError):
            permissions.asignar_sede(self.analista_libre, self.escuela)
        self.assertFalse(permissions.asignar_sede(self.analista_a, self.sede_a)["creada"])
        self.assertEqual(
            frappe.db.count("User Permission", {"user": self.analista_a, "allow": "Unidad Organica"}), 1
        )
