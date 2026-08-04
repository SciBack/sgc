# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Modelo canónico de autorización: ámbitos, Role Profiles y auditoría (issue #5).

Complementa `test_permissions.py`, que cubre el acotamiento por Programa Sede
implementado a mano. Aquí se prueban las piezas del spec M07+M16 que el
framework debería resolver SIN código propio:

  - Acotamiento por `Unidad Organica` (sede) y por `Proceso`, que son DocTypes
    árbol con Link directo en los documentos.
  - Recursión: una User Permission sobre un nodo padre alcanza sus descendientes.
  - Composición: dos dimensiones distintas se intersectan (AND).
  - Semántica del ámbito vacío: un registro sin ámbito es visible para todos.
  - Opt-in: sin User Permission sembrada, el usuario ve todo.

La hipótesis que estos tests verifican es la del spec: **para un DocType con Link
directo al ámbito no hace falta escribir nada**; el motor de permisos de Frappe
ya genera la condición. Si estos tests pasan sin tocar `permissions.py`, la
extensión a sede y proceso es configuración, no desarrollo.

Convenciones (ver test_permissions.py): IntegrationTestCase con rollback por
test, usuarios y User Permission creados dentro del caso, y toda operación de
doc con ignore_permissions=True.
"""
import frappe
from frappe.permissions import add_permission, update_permission_property
from frappe.tests import IntegrationTestCase

from sgc.setup import f3b_rbac
from sgc.tests import factories

PREFIJO = "TAMB"

# Rol NO exento (ver permissions.ROLES_EXENTOS): es el que puede quedar acotado.
ROL_ACOTADO = "Responsable de Calidad de Programa"


class IntegrationTestRoleProfiles(IntegrationTestCase):
    """D1 del spec: los Role Profiles llevan el nombre institucional."""

    def setUp(self):
        frappe.set_user("Administrator")

    def test_los_role_profiles_canonicos_existen_con_sus_roles(self):
        """Cada Role Profile declarado agrupa exactamente los roles de su spec."""
        for nombre, roles_esperados in f3b_rbac.ROLE_PROFILES.items():
            self.assertTrue(
                frappe.db.exists("Role Profile", nombre),
                f"falta el Role Profile «{nombre}»",
            )
            rp = frappe.get_doc("Role Profile", nombre)
            self.assertEqual(
                sorted(r.role for r in rp.roles),
                sorted(roles_esperados),
                f"el Role Profile «{nombre}» no agrupa los roles esperados",
            )

    def test_administrador_sgc_no_incluye_system_manager(self):
        """El gobierno funcional del SGC no arrastra la administración técnica.

        Colapsarlos elimina el control interno más básico: quien gobierna el
        contenido de calidad no debe poder tocar la plataforma.
        """
        roles = f3b_rbac.ROLE_PROFILES["Administrador SGC"]
        self.assertNotIn("System Manager", roles)


class IntegrationTestAmbitos(IntegrationTestCase):
    """Acotamiento por sede y proceso: ¿lo resuelve el framework solo?"""

    def setUp(self):
        frappe.set_user("Administrator")
        self._user_prev = frappe.session.user

        # `Riesgo` tiene Workflow activo: insertar en un estado que no sea el
        # inicial lanza WorkflowPermissionError sin importar el rol. Aquí solo se
        # usa como portador de dos Links de ámbito, así que el workflow estorba.
        factories.desactivar_workflow("Riesgo")

        # --- árbol de unidades: una sede con dos facultades colgando ---
        self.sede = self._unidad(f"{PREFIJO}-SEDE", tipo="Sede", is_group=1)
        self.facultad = self._unidad(f"{PREFIJO}-FAC", tipo="Facultad", parent=self.sede)
        self.otra_sede = self._unidad(f"{PREFIJO}-SEDE2", tipo="Sede", is_group=1)

        # --- árbol de procesos: un macroproceso con un subproceso ---
        self.proc_padre = self._proceso(f"{PREFIJO}-P1", is_group=1)
        self.proc_hijo = self._proceso(f"{PREFIJO}-P2", parent=self.proc_padre)
        self.proc_ajeno = self._proceso(f"{PREFIJO}-P9")

        # --- documentos anclados a cada ámbito ---
        self.obj_sede = self._objetivo(f"{PREFIJO}-OBJ-SEDE", self.sede)
        self.obj_facultad = self._objetivo(f"{PREFIJO}-OBJ-FAC", self.facultad)
        self.obj_otra = self._objetivo(f"{PREFIJO}-OBJ-OTRA", self.otra_sede)
        self.obj_sin_ambito = self._objetivo(f"{PREFIJO}-OBJ-NULL", None)

        for dt in ("Objetivo Calidad", "Riesgo"):
            self._ensure_lectura(ROL_ACOTADO, dt)

    def tearDown(self):
        frappe.set_user(self._user_prev)

    # ------------------------------------------------------------- factories
    def _unidad(self, codigo, tipo="Unidad", parent=None, is_group=0):
        if frappe.db.exists("Unidad Organica", codigo):
            return codigo
        doc = frappe.get_doc({
            "doctype": "Unidad Organica", "codigo": codigo,
            "nombre": f"Unidad {codigo}", "tipo": tipo, "is_group": is_group,
            "parent_unidad_organica": parent,
        })
        doc.insert(ignore_permissions=True)
        return doc.name

    def _proceso(self, codigo, parent=None, is_group=0):
        if frappe.db.exists("Proceso", codigo):
            return codigo
        doc = frappe.get_doc({
            "doctype": "Proceso", "codigo": codigo, "proceso": f"Proceso {codigo}",
            "nivel": "Estratégico", "is_group": is_group, "parent_proceso": parent,
        })
        doc.insert(ignore_permissions=True)
        return doc.name

    def _objetivo(self, codigo, unidad):
        if frappe.db.exists("Objetivo Calidad", codigo):
            frappe.delete_doc("Objetivo Calidad", codigo, force=True, ignore_permissions=True)
        doc = frappe.get_doc({
            "doctype": "Objetivo Calidad", "codigo": codigo, "unidad_organica": unidad,
        })
        doc.insert(ignore_permissions=True)
        return doc.name

    def _riesgo(self, titulo, unidad=None, proceso=None):
        doc = frappe.get_doc({
            "doctype": "Riesgo", "titulo": titulo,
            "unidad_organica": unidad, "proceso": proceso,
        })
        doc.insert(ignore_permissions=True)
        return doc.name

    def _ensure_lectura(self, role, doctype):
        add_permission(doctype, role, 0)
        update_permission_property(doctype, role, 0, "read", 1, validate=False)

    def _crear_usuario(self, local, ambitos=None):
        """Usuario con `ROL_ACOTADO` y las User Permission de `ambitos`.

        `ambitos` es una lista de (doctype, valor). Sin ámbitos, el usuario queda
        sin ninguna User Permission (caso opt-in inactivo).
        """
        email = f"{local}@{PREFIJO.lower()}.test"
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.get_doc({
            "doctype": "User", "email": email, "first_name": local,
            "send_welcome_email": 0, "roles": [{"role": ROL_ACOTADO}],
        }).insert(ignore_permissions=True)
        for allow, for_value in (ambitos or []):
            frappe.get_doc({
                "doctype": "User Permission", "user": email,
                "allow": allow, "for_value": for_value,
            }).insert(ignore_permissions=True)
        return email

    def _listar(self, doctype, user, filtros=None):
        frappe.set_user(user)
        try:
            return set(frappe.get_list(doctype, filters=filtros or {}, pluck="name"))
        finally:
            frappe.set_user("Administrator")

    # =====================================================================
    # Sede — DocType árbol con Link directo
    # =====================================================================
    def test_user_permission_de_sede_acota_sin_codigo_propio(self):
        """Una User Permission sobre la sede basta: no hay hook para este DocType."""
        user = self._crear_usuario("amb-sede", [("Unidad Organica", self.sede)])

        visibles = self._listar("Objetivo Calidad", user)

        self.assertIn(self.obj_sede, visibles)
        self.assertNotIn(self.obj_otra, visibles, "ve el objetivo de OTRA sede")

    def test_user_permission_de_sede_alcanza_descendientes(self):
        """El nodo padre arrastra a sus hijos: es el scoping recursivo del árbol.

        Sin esto, un responsable de sede tendría que recibir una User Permission
        por cada facultad, y cada facultad nueva rompería su acceso.
        """
        user = self._crear_usuario("amb-desc", [("Unidad Organica", self.sede)])

        visibles = self._listar("Objetivo Calidad", user)

        self.assertIn(self.obj_facultad, visibles,
                      "la User Permission sobre la sede no alcanzó a la facultad hija")

    def test_registro_sin_ambito_es_visible(self):
        """Lo no atribuible a un ámbito es transversal, no se oculta.

        Es la semántica del propio framework (`ifnull(campo,'')=''`) y la que ya
        aplica el acotamiento por programa.
        """
        user = self._crear_usuario("amb-null", [("Unidad Organica", self.sede)])

        self.assertIn(self.obj_sin_ambito, self._listar("Objetivo Calidad", user))

    def test_opt_in_sin_user_permission_ve_todo(self):
        """Sin ninguna User Permission sembrada, el mecanismo está inactivo."""
        user = self._crear_usuario("amb-libre")

        visibles = self._listar("Objetivo Calidad", user)

        self.assertIn(self.obj_sede, visibles)
        self.assertIn(self.obj_otra, visibles)

    # =====================================================================
    # Proceso — DocType árbol con Link directo
    # =====================================================================
    def test_user_permission_de_proceso_acota_y_alcanza_subprocesos(self):
        r_padre = self._riesgo(f"{PREFIJO} riesgo del proceso padre", proceso=self.proc_padre)
        r_hijo = self._riesgo(f"{PREFIJO} riesgo del subproceso", proceso=self.proc_hijo)
        r_ajeno = self._riesgo(f"{PREFIJO} riesgo ajeno", proceso=self.proc_ajeno)
        user = self._crear_usuario("amb-proc", [("Proceso", self.proc_padre)])

        visibles = self._listar("Riesgo", user)

        self.assertIn(r_padre, visibles)
        self.assertIn(r_hijo, visibles, "no alcanzó al subproceso")
        self.assertNotIn(r_ajeno, visibles, "ve el riesgo de un proceso ajeno")

    # =====================================================================
    # Composición de dimensiones
    # =====================================================================
    def test_dos_dimensiones_se_intersectan(self):
        """Sede Y proceso a la vez: el usuario ve solo lo que cumple ambas.

        El motor une las condiciones de doctypes distintos con AND; varias del
        mismo doctype con OR.
        """
        ok = self._riesgo(f"{PREFIJO} cumple ambas", unidad=self.sede, proceso=self.proc_padre)
        solo_sede = self._riesgo(f"{PREFIJO} solo sede", unidad=self.sede, proceso=self.proc_ajeno)
        solo_proc = self._riesgo(f"{PREFIJO} solo proceso", unidad=self.otra_sede,
                                 proceso=self.proc_padre)
        user = self._crear_usuario("amb-and", [
            ("Unidad Organica", self.sede),
            ("Proceso", self.proc_padre),
        ])

        visibles = self._listar("Riesgo", user)

        self.assertIn(ok, visibles)
        self.assertNotIn(solo_sede, visibles, "no aplicó la restricción de proceso")
        self.assertNotIn(solo_proc, visibles, "no aplicó la restricción de sede")

    def test_dos_valores_de_la_misma_dimension_se_suman(self):
        """Dos sedes asignadas: el usuario ve ambas (unión, no intersección)."""
        user = self._crear_usuario("amb-or", [
            ("Unidad Organica", self.sede),
            ("Unidad Organica", self.otra_sede),
        ])

        visibles = self._listar("Objetivo Calidad", user)

        self.assertIn(self.obj_sede, visibles)
        self.assertIn(self.obj_otra, visibles)


class IntegrationTestAuditoria(IntegrationTestCase):
    """M16: el auditor lee cambios de datos, nunca sesiones."""

    # Datos críticos según el requerimiento: niveles de logro, indicadores,
    # cumplimiento de condiciones básicas y versiones documentales.
    DOCTYPES_CRITICOS = (
        "Valoracion Estandar",
        "Valoracion Criterio",
        "Valor Indicador",
        "Documento Controlado",
    )

    def setUp(self):
        frappe.set_user("Administrator")

    def test_doctypes_criticos_registran_cambios(self):
        """`track_changes` es lo que hace que exista el valor anterior.

        Sin él no hay `Version`, y el requisito de registrar toda modificación de
        dato crítico con usuario, fecha y valor anterior queda incumplido en
        silencio: nadie nota que no se está guardando nada.
        """
        for dt in self.DOCTYPES_CRITICOS:
            self.assertTrue(
                frappe.db.get_value("DocType", dt, "track_changes"),
                f"«{dt}» es un dato crítico y no tiene track_changes activo",
            )

    def test_auditor_lee_el_registro_de_cambios(self):
        self.assertTrue(
            frappe.db.exists("Custom DocPerm", {"role": "Auditor Interno", "parent": "Version"})
            or frappe.db.exists("DocPerm", {"role": "Auditor Interno", "parent": "Version"}),
            "el Auditor Interno no tiene lectura sobre Version",
        )

    def test_auditor_no_accede_al_registro_de_sesiones(self):
        """Quién entró, cuándo y desde qué IP es dato personal del trabajador.

        El auditor audita el sistema de calidad, no vigila a las personas: sin
        finalidad declarada ni base legal, exponerle las sesiones sería
        tratamiento de datos personales sin sustento.
        """
        for tabla in ("Custom DocPerm", "DocPerm"):
            self.assertFalse(
                frappe.db.exists(tabla, {"role": "Auditor Interno", "parent": "Activity Log"}),
                "el Auditor Interno tiene acceso al registro de sesiones",
            )
