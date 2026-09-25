# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""La acción de mejora deja su tarea en la lista de pendientes del responsable (#35).

Lo que se comprueba es el contrato de `sgc/tareas.py` visto desde la acción:

  - con responsable, en Planificada o En ejecucion  -> una tarea abierta suya,
    con la fecha de compromiso como vencimiento
  - guardar otra vez                                -> no duplica
  - cambia la fecha                                 -> cambia el vencimiento
  - cambia el responsable                           -> la del anterior se cancela
  - Ejecutada                                       -> la tarea se cierra
  - Reabrir                                         -> vuelve una tarea abierta
  - la tarea es recordatorio, no registro           -> cerrarla no mueve la acción
  - quien guarda no necesita permiso de «compartir» -> y no se comparte nada

Todo se deshace al final de cada test (rollback de `IntegrationTestCase`).
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from sgc.tests import factories

RESPONSABLE = "sgc-prueba-tarea@example.com"
OTRO = "sgc-prueba-tarea-otro@example.com"
SIN_ROLES = "sgc-prueba-tarea-sinroles@example.com"
QUIEN_GUARDA = "sgc-prueba-tarea-guarda@example.com"

ROL_LECTURA = "Dueño de Proceso"


def _usuario(correo, roles=()):
    if not frappe.db.exists("User", correo):
        u = frappe.get_doc(
            {"doctype": "User", "email": correo, "first_name": correo.split("@")[0], "send_welcome_email": 0}
        )
        for rol in roles:
            u.append("roles", {"role": rol})
        u.insert(ignore_permissions=True)
    return correo


class IntegrationTestTareas(IntegrationTestCase):
    def setUp(self):
        factories.desactivar_workflow("Accion Mejora")
        factories.desactivar_workflow("Plan Mejora")
        for correo in (RESPONSABLE, OTRO):
            _usuario(correo, [ROL_LECTURA])
        _usuario(SIN_ROLES)
        _usuario(QUIEN_GUARDA, [ROL_LECTURA])
        self.evidencia = factories.crear_evidencia().name

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    # -- helpers -----------------------------------------------------------
    def _accion(self, **overrides):
        vals = {
            "doctype": "Accion Mejora",
            "descripcion": "Acción de prueba de tareas",
            "tipo": "Correctiva",
            "estado": "Planificada",
            "responsable": RESPONSABLE,
            "fecha_compromiso": add_days(nowdate(), 30),
        }
        vals.update(overrides)
        return frappe.get_doc(vals).insert(ignore_permissions=True)

    def _mover(self, acc, estado=None, **campos):
        if estado:
            acc.estado = estado
        for k, v in campos.items():
            acc.set(k, v)
        acc.save(ignore_permissions=True)
        return acc

    def _tareas(self, acc, **filtros):
        return frappe.get_all(
            "ToDo",
            filters={"reference_type": "Accion Mejora", "reference_name": acc.name, **filtros},
            fields=["name", "allocated_to", "status", "date", "assigned_by", "description"],
            order_by="creation",
        )

    # -- alta --------------------------------------------------------------
    def test_asignar_responsable_le_crea_una_tarea_con_la_fecha_de_compromiso(self):
        acc = self._accion()
        tareas = self._tareas(acc)
        self.assertEqual(len(tareas), 1)
        self.assertEqual(tareas[0].allocated_to, RESPONSABLE)
        self.assertEqual(tareas[0].status, "Open")
        self.assertEqual(getdate(tareas[0].date), getdate(acc.fecha_compromiso))
        self.assertIn(acc.codigo, tareas[0].description)

    def test_la_accion_muestra_a_quien_esta_asignada(self):
        """El `_assign` del documento es lo que pinta la barra lateral y la lista."""
        acc = self._accion()
        self.assertIn(RESPONSABLE, frappe.db.get_value("Accion Mejora", acc.name, "_assign"))

    def test_sin_responsable_no_hay_tarea(self):
        acc = self._accion(responsable=None)
        self.assertEqual(self._tareas(acc), [])

    def test_guardar_otra_vez_no_duplica(self):
        acc = self._accion()
        self._mover(acc, descripcion="Otra redacción")
        self._mover(acc)
        self.assertEqual(len(self._tareas(acc)), 1)

    def test_cambiar_la_fecha_mueve_el_vencimiento(self):
        acc = self._accion()
        nueva = add_days(nowdate(), 60)
        self._mover(acc, fecha_compromiso=nueva)
        tareas = self._tareas(acc, status="Open")
        self.assertEqual(len(tareas), 1)
        self.assertEqual(getdate(tareas[0].date), getdate(nueva))

    def test_cambiar_el_responsable_cancela_la_del_anterior(self):
        """No la terminó: dejó de ser suya. Por eso Cancelled y no Closed."""
        acc = self._accion()
        self._mover(acc, responsable=OTRO)
        por_usuario = {t.allocated_to: t.status for t in self._tareas(acc)}
        self.assertEqual(por_usuario, {RESPONSABLE: "Cancelled", OTRO: "Open"})

    # -- avance del ciclo --------------------------------------------------
    def test_ejecutarla_cierra_la_tarea(self):
        acc = self._accion()
        self._mover(acc, "En ejecucion")
        self.assertEqual(len(self._tareas(acc, status="Open")), 1)
        self._mover(acc, "Ejecutada")
        self.assertEqual([t.status for t in self._tareas(acc)], ["Closed"])

    def test_reabrirla_devuelve_la_tarea(self):
        acc = self._accion()
        self._mover(acc, "En ejecucion")
        self._mover(acc, "Ejecutada")
        self._mover(acc, "Verificada no eficaz")
        self.assertEqual(self._tareas(acc, status="Open"), [])
        self._mover(acc, "En ejecucion")
        self.assertEqual(len(self._tareas(acc, status="Open")), 1)

    def test_alta_directa_en_estado_cerrado_no_crea_tarea(self):
        """Una semilla que aterriza ya ejecutada no le deja trabajo a nadie."""
        acc = self._accion(estado="Ejecutada")
        self.assertEqual(self._tareas(acc), [])

    # -- frontera: recordatorio, no registro ------------------------------
    def test_cerrar_la_tarea_no_mueve_la_accion(self):
        acc = self._accion()
        tarea = frappe.get_doc("ToDo", self._tareas(acc)[0].name)
        tarea.status = "Closed"
        tarea.save(ignore_permissions=True)
        self.assertEqual(frappe.db.get_value("Accion Mejora", acc.name, "estado"), "Planificada")

    # -- aviso y permisos --------------------------------------------------
    def test_el_responsable_recibe_el_aviso_de_asignacion(self):
        acc = self._accion()
        avisos = frappe.get_all(
            "Notification Log",
            filters={
                "for_user": RESPONSABLE,
                "type": "Assignment",
                "document_type": "Accion Mejora",
                "document_name": acc.name,
            },
        )
        self.assertEqual(len(avisos), 1)

    def test_quien_guarda_no_necesita_permiso_de_compartir(self):
        """`assign_to.add` compartiría el documento con un responsable sin lectura, y
        compartir exige un permiso que la matriz RBAC no da a nadie: guardar fallaría."""
        self.assertFalse(frappe.has_permission("Accion Mejora", "share", user=QUIEN_GUARDA))
        frappe.set_user(QUIEN_GUARDA)
        acc = self._accion(responsable=SIN_ROLES)
        frappe.set_user("Administrator")
        self.assertEqual([t.allocated_to for t in self._tareas(acc)], [SIN_ROLES])
        self.assertEqual(self._tareas(acc)[0].assigned_by, QUIEN_GUARDA)
        self.assertFalse(
            frappe.db.exists("DocShare", {"share_doctype": "Accion Mejora", "share_name": acc.name})
        )

    def test_un_usuario_deshabilitado_no_recibe_tarea(self):
        frappe.db.set_value("User", OTRO, "enabled", 0)
        acc = self._accion(responsable=OTRO)
        self.assertEqual(self._tareas(acc), [])
