# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.setup.f15_notificaciones_workflow` — notificaciones en
transiciones REALES del workflow de Informe Cumplimiento (M17 fase 2).

Cubre que `run()`:
- Crea las 2 `Notification` declarativas ("... aprobado" / "... presentado a
  SUNEDU"), `event="Value Change"` sobre `estado`, canal System, attach_print=0.
- Es idempotente.
- Dispara DE VERDAD al transicionar el doc vía `.save()` (Borrador -> En
  revisión -> Aprobado -> Presentado a SUNEDU, la cadena real del workflow de
  f11) -- crea una fila en `Notification Log` para el usuario con el rol
  destinatario. Y NO dispara en un `save()` que no cambia `estado`.

Gotcha (ver f7_notificaciones.py / f11_workflow_cumplimiento.py): sus `run()`
dejan `frappe.flags.in_patch = True` sin resetear -- necesario para que el
propio upsert de configuración no dispare notificaciones a medio construir.
Si no se apaga antes de transicionar el doc de prueba, `Document.run_notifications()`
hace no-op silencioso (ver `frappe.model.document.Document.run_notifications`)
y el test "pasaría" sin haber probado nada. Por eso el setUp llama a `f15.run()`
y EXPLÍCITAMENTE apaga el flag después, antes de cualquier `.save()` de prueba.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f15_notificaciones_workflow as f15
from sgc.tests import factories

PREFIJO = "TEST-M17W"


class IntegrationTestNotificacionesWorkflow(IntegrationTestCase):
    def setUp(self):
        self._user_prev = frappe.session.user
        frappe.set_user("Administrator")

        # Idempotente: deja las 2 Notification registradas aunque el site de
        # test no haya pasado (todavía) por `bench migrate` (after_migrate).
        f15.run()
        # Ver docstring del módulo: f15.run() (como f7/f11) deja in_patch=True;
        # apagarlo es lo que permite que las transiciones de abajo disparen
        # la Notification de verdad en vez de un no-op silencioso.
        frappe.flags.in_patch = False

        arbol = factories.crear_marco_prueba(
            n_estandares=1, n_criterios=0, prefijo=PREFIJO
        )
        self.marco = arbol["marco"]

        # Notification Recipient por rol solo resuelve a Usuarios reales con
        # ese rol (Administrator no cuenta: se resuelve aparte y queda
        # excluido de la tabla Has Role) -- sin esto, get_info_based_on_role
        # devuelve una lista vacía y create_system_notification no crea nada.
        self.aprobador = self._crear_usuario("aprobador", "Autoridad Aprobadora")
        self.dpgc = self._crear_usuario("dpgc", "DPGC")

    def tearDown(self):
        frappe.set_user(self._user_prev)

    # ------------------------------------------------------------ helpers

    def _crear_usuario(self, local, rol):
        email = f"{local}@{PREFIJO.lower()}.test"
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.get_doc({
            "doctype": "User", "email": email, "first_name": local,
            "send_welcome_email": 0, "roles": [{"role": rol}],
        }).insert(ignore_permissions=True)
        return email

    def _informe_aprobable(self, anio):
        """Crea un Informe Cumplimiento con sus CBC evaluadas (Cumple), en
        Borrador -- listo para recorrer la cadena real del workflow.

        `setUp()` llama `f15.run()`, que comitea (necesario en producción)
        -- eso rompe el rollback automático de este test y deja el
        `IAC-{anio}` (autoname) permanentemente en BD. Sin este guard, una
        segunda corrida separada de `bench run-tests` choca con
        `DuplicateEntryError` al reinsertar el mismo nombre.
        """
        nombre = f"IAC-{anio}"
        if frappe.db.exists("Informe Cumplimiento", nombre):
            frappe.delete_doc("Informe Cumplimiento", nombre, force=True, ignore_permissions=True)
        # Notification Log no se borra en cascada con el documento -- residuo
        # de una corrida anterior con el MISMO nombre inflaría el conteo de
        # `_logs()` (mismo document_name) aunque el Informe ya no exista.
        frappe.db.delete("Notification Log", {
            "document_type": "Informe Cumplimiento", "document_name": nombre,
        })

        doc = frappe.new_doc("Informe Cumplimiento")
        doc.anio = anio
        doc.marco_normativo = self.marco
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)  # autopobla CBC, arranca en Borrador
        for c in doc.condiciones:
            c.cumple = factories.CUMPLE
        doc.save(ignore_permissions=True)
        return doc

    def _logs(self, doc, for_user, subject_like):
        return frappe.get_all(
            "Notification Log",
            filters={
                "document_type": "Informe Cumplimiento",
                "document_name": doc.name,
                "for_user": for_user,
                "subject": ["like", subject_like],
            },
        )

    # ------------------------------------------------------------ run() declarativo

    def test_run_crea_las_dos_reglas(self):
        notifs = frappe.get_all(
            "Notification",
            filters={"name": ["like", "SGC - Informe Cumplimiento%"]},
            fields=[
                "name", "document_type", "event", "value_changed",
                "channel", "attach_print", "enabled",
            ],
        )
        self.assertEqual(len(notifs), 2)
        for n in notifs:
            self.assertEqual(n["document_type"], "Informe Cumplimiento")
            self.assertEqual(n["event"], "Value Change")
            self.assertEqual(n["value_changed"], "estado")
            self.assertEqual(n["channel"], "System Notification")
            self.assertEqual(n["attach_print"], 0)
            self.assertEqual(n["enabled"], 1)

    def test_run_es_idempotente(self):
        f15.run()
        frappe.flags.in_patch = False
        notifs = frappe.get_all(
            "Notification", filters={"name": ["like", "SGC - Informe Cumplimiento%"]}
        )
        self.assertEqual(len(notifs), 2)

    # ------------------------------------------------------------ dispara en transición real

    def test_aprobado_notifica_a_autoridad_aprobadora(self):
        doc = self._informe_aprobable(3001)
        doc.estado = "En revisión"
        doc.save(ignore_permissions=True)
        self.assertEqual(len(self._logs(doc, self.aprobador, "%Aprobado%")), 0)

        doc.estado = "Aprobado"
        doc.save(ignore_permissions=True)

        self.assertEqual(len(self._logs(doc, self.aprobador, "%Aprobado%")), 1)
        # DPGC (destinatario de la OTRA regla) no debe recibir esta.
        self.assertEqual(len(self._logs(doc, self.dpgc, "%Aprobado%")), 0)

    def test_presentado_notifica_a_dpgc(self):
        doc = self._informe_aprobable(3002)
        for estado in ("En revisión", "Aprobado"):
            doc.estado = estado
            doc.save(ignore_permissions=True)
        self.assertEqual(len(self._logs(doc, self.dpgc, "%SUNEDU%")), 0)

        doc.estado = "Presentado a SUNEDU"
        doc.save(ignore_permissions=True)

        self.assertEqual(len(self._logs(doc, self.dpgc, "%SUNEDU%")), 1)

    def test_no_notifica_en_save_sin_cambio_de_estado(self):
        """Guardar sin tocar `estado` NO dispara -- la garantía central del
        diseño (a diferencia de `send_email_alert` nativo del Workflow, que
        reevaluaba en cualquier save y rompió 70 tests)."""
        doc = self._informe_aprobable(3003)
        for estado in ("En revisión", "Aprobado"):
            doc.estado = estado
            doc.save(ignore_permissions=True)
        antes = len(self._logs(doc, self.aprobador, "%Aprobado%"))
        self.assertEqual(antes, 1)

        doc.resumen = "actualización de resumen, no de estado"
        doc.save(ignore_permissions=True)

        despues = len(self._logs(doc, self.aprobador, "%Aprobado%"))
        self.assertEqual(despues, antes)
