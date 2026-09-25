# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""El plan de actividades de la auditoría y las tareas de sus responsables (#35).

  - una tarea por responsable, no por actividad   -> vence en su próxima pendiente
  - hacer una actividad                            -> la tarea pasa a la siguiente
  - hacerlas todas                                 -> la tarea se cierra
  - quitarle sus actividades                       -> la tarea se cancela
  - cerrar la auditoría con algo sin hacer         -> se cancela, no se da por hecho
  - quién marcó «realizada» lo sella el sistema    -> y lo tecleado no prevalece

Todo se deshace al final de cada test (rollback de `IntegrationTestCase`).
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from sgc.tests import factories

AUDITOR = "sgc-prueba-actividad-auditor@example.com"
AUDITADO = "sgc-prueba-actividad-auditado@example.com"
ADMIN = "Administrator"


def _usuario(correo):
    if not frappe.db.exists("User", correo):
        frappe.get_doc(
            {"doctype": "User", "email": correo, "first_name": correo.split("@")[0], "send_welcome_email": 0}
        ).insert(ignore_permissions=True)


def _dia(n):
    return add_days(nowdate(), n)


class IntegrationTestActividadesAuditoria(IntegrationTestCase):
    def setUp(self):
        factories.desactivar_workflow("Auditoria")
        _usuario(AUDITOR)
        _usuario(AUDITADO)

    def tearDown(self):
        frappe.set_user(ADMIN)
        frappe.db.rollback()

    # -- helpers -----------------------------------------------------------
    def _auditoria(self, actividades, **overrides):
        vals = {
            "doctype": "Auditoria",
            "titulo": "Auditoría de prueba de actividades",
            "tipo": "Interna",
            "estado": "Planificada",
            "actividades": actividades,
        }
        vals.update(overrides)
        return frappe.get_doc(vals).insert(ignore_permissions=True)

    def _plan(self):
        return [
            {"fecha": _dia(5), "actividad": "Reunión de apertura", "responsable": AUDITOR},
            {"fecha": _dia(3), "actividad": "Revisión documental", "responsable": AUDITOR},
            {"fecha": _dia(4), "actividad": "Entregar registros de 2025", "responsable": AUDITADO},
        ]

    def _tareas(self, aud, **filtros):
        return frappe.get_all(
            "ToDo",
            filters={"reference_type": "Auditoria", "reference_name": aud.name, **filtros},
            fields=["allocated_to", "status", "date", "description"],
            order_by="creation",
        )

    def _abiertas(self, aud):
        return {t.allocated_to: t for t in self._tareas(aud, status="Open")}

    def _fila(self, aud, actividad):
        return next(f for f in aud.actividades if f.actividad == actividad)

    def _marcar(self, aud, *actividades):
        for a in actividades:
            self._fila(aud, a).realizada = 1
        aud.save(ignore_permissions=True)
        return aud

    # -- una tarea por responsable ----------------------------------------
    def test_una_tarea_por_responsable_con_su_proxima_actividad(self):
        aud = self._auditoria(self._plan())
        abiertas = self._abiertas(aud)
        self.assertEqual(set(abiertas), {AUDITOR, AUDITADO})
        self.assertEqual(len(self._tareas(aud)), 2, "dos actividades del auditor, una sola tarea")
        self.assertEqual(getdate(abiertas[AUDITOR].date), getdate(_dia(3)))
        self.assertIn("2 actividad(es)", abiertas[AUDITOR].description)
        self.assertIn("Revisión documental", abiertas[AUDITOR].description)

    def test_una_actividad_sin_responsable_no_crea_tarea(self):
        aud = self._auditoria([{"fecha": _dia(2), "actividad": "Cierre"}])
        self.assertEqual(self._tareas(aud), [])

    # -- avance -------------------------------------------------------------
    def test_hacer_una_actividad_pasa_la_tarea_a_la_siguiente(self):
        aud = self._auditoria(self._plan())
        self._marcar(aud, "Revisión documental")
        tarea = self._abiertas(aud)[AUDITOR]
        self.assertEqual(getdate(tarea.date), getdate(_dia(5)))
        self.assertIn("1 actividad(es)", tarea.description)
        self.assertIn("Reunión de apertura", tarea.description)

    def test_hacerlas_todas_cierra_su_tarea_y_no_la_de_los_demas(self):
        aud = self._auditoria(self._plan())
        self._marcar(aud, "Revisión documental", "Reunión de apertura")
        estados = {t.allocated_to: t.status for t in self._tareas(aud)}
        self.assertEqual(estados, {AUDITOR: "Closed", AUDITADO: "Open"})

    def test_desmarcar_una_actividad_devuelve_la_tarea(self):
        aud = self._auditoria(self._plan())
        self._marcar(aud, "Entregar registros de 2025")
        self.assertNotIn(AUDITADO, self._abiertas(aud))
        self._fila(aud, "Entregar registros de 2025").realizada = 0
        aud.save(ignore_permissions=True)
        self.assertIn(AUDITADO, self._abiertas(aud))

    def test_quitarle_sus_actividades_cancela_su_tarea(self):
        aud = self._auditoria(self._plan())
        aud.actividades = [f for f in aud.actividades if f.responsable != AUDITADO]
        aud.save(ignore_permissions=True)
        estados = {t.allocated_to: t.status for t in self._tareas(aud)}
        self.assertEqual(estados[AUDITADO], "Cancelled")

    def test_cambiar_la_fecha_mueve_el_vencimiento(self):
        aud = self._auditoria(self._plan())
        self._fila(aud, "Entregar registros de 2025").fecha = _dia(10)
        aud.save(ignore_permissions=True)
        self.assertEqual(getdate(self._abiertas(aud)[AUDITADO].date), getdate(_dia(10)))

    def test_cerrar_la_auditoria_cancela_lo_que_no_se_hizo(self):
        """Hecho = Closed; sin hacer = Cancelled. Cerrar no convierte en hecho lo pendiente."""
        aud = self._auditoria(
            self._plan(),
            equipo=[{"usuario": AUDITOR, "rol": "Auditor lider", "independiente_del_area": 1}],
            criterios=[{"tipo_criterio": "Clausula norma", "referencia": "ISO 9001 9.2"}],
        )
        self._marcar(aud, "Revisión documental", "Reunión de apertura")
        informe = frappe.get_doc(
            {"doctype": "Informe Auditoria", "auditoria": aud.name, "conclusiones": "Prueba."}
        ).insert(ignore_permissions=True)
        aud.informe = informe.name
        aud.estado = "Cerrada"  # sin recorrer el ciclo: el workflow está desactivado
        aud.save(ignore_permissions=True)
        estados = {t.allocated_to: t.status for t in self._tareas(aud)}
        self.assertEqual(estados, {AUDITOR: "Closed", AUDITADO: "Cancelled"})

    # -- firma sellada -----------------------------------------------------
    def test_quien_marca_realizada_lo_sella_el_sistema(self):
        aud = self._auditoria(self._plan())
        fila = self._fila(aud, "Revisión documental")
        fila.realizada = 1
        fila.realizada_por = AUDITADO  # lo tecleado no prevalece
        aud.save(ignore_permissions=True)
        fila = self._fila(aud, "Revisión documental")
        self.assertEqual(fila.realizada_por, ADMIN)
        self.assertEqual(getdate(fila.realizada_el), getdate(nowdate()))

    def test_la_firma_no_se_reescribe_al_guardar_otra_vez(self):
        aud = self._auditoria(self._plan())
        self._marcar(aud, "Revisión documental")
        self._fila(aud, "Revisión documental").realizada_por = AUDITADO
        aud.save(ignore_permissions=True)
        self.assertEqual(self._fila(aud, "Revisión documental").realizada_por, ADMIN)

    def test_desmarcar_borra_la_firma(self):
        aud = self._auditoria(self._plan())
        self._marcar(aud, "Revisión documental")
        self._fila(aud, "Revisión documental").realizada = 0
        aud.save(ignore_permissions=True)
        fila = self._fila(aud, "Revisión documental")
        self.assertIsNone(fila.realizada_por)
        self.assertIsNone(fila.realizada_el)

    def test_la_tarea_es_recordatorio_no_registro(self):
        """Cerrar la tarea desde la lista de pendientes no marca la actividad."""
        aud = self._auditoria(self._plan())
        nombre = frappe.get_all(
            "ToDo",
            filters={"reference_type": "Auditoria", "reference_name": aud.name, "allocated_to": AUDITADO},
            pluck="name",
        )[0]
        tarea = frappe.get_doc("ToDo", nombre)
        tarea.status = "Closed"
        tarea.save(ignore_permissions=True)
        aud.reload()
        self.assertFalse(self._fila(aud, "Entregar registros de 2025").realizada)
