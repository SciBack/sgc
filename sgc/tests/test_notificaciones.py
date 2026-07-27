# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.setup.f7_notificaciones` — reglas de alerta del SGC (M17).

Cubre que `run()`:
- Crea las 5 Notification declaradas en `f7.NOTIFICACIONES`: 4 de vencimiento
  (Documento Controlado, Evidencia, Accion Mejora, Plan Mejora; event="Days
  Before") + 1 de convocatoria (Reunion; event="New").
- Es idempotente (re-ejecutar no duplica: actualiza en sitio).

`_sgc_notifs()` filtra por los NOMBRES exactos que `f7.NOTIFICACIONES` declara,
no por un prefijo `"SGC%"` global: otros módulos (p.ej. f15_notificaciones_workflow)
también crean `Notification` con el mismo prefijo `"SGC - ..."`, y un filtro
por prefijo contaría las suyas también, dando un conteo inflado y falso.
"""

import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f7_notificaciones as f7


class IntegrationTestNotificaciones(IntegrationTestCase):
    def _sgc_notifs(self):
        nombres = [cfg["name"] for cfg in f7.NOTIFICACIONES]
        return frappe.get_all(
            "Notification",
            filters={"name": ["in", nombres]},
            fields=["name", "document_type", "event", "date_changed", "channel", "enabled"],
        )

    def test_run_crea_las_cinco_reglas(self):
        """run() deja 5 Notification 'SGC …' activas.

        NO se asserta el canal: `run()` solo lo fija al CREAR y respeta el que
        exista al actualizar (ver `test_run_respeta_el_canal_configurado`). El
        canal es configuración de runtime, no del código.
        """
        f7.run()
        notifs = self._sgc_notifs()
        self.assertEqual(len(notifs), 5)
        for n in notifs:
            self.assertEqual(n["enabled"], 1)
            if n["event"] == "Days Before":
                self.assertTrue(n["date_changed"])  # el campo fecha a vigilar
            else:
                # La regla de convocatoria (Reunion) dispara por evento "New",
                # no tiene campo de fecha a vigilar.
                self.assertEqual(n["event"], "New")

    def test_run_respeta_el_canal_configurado(self):
        """Regresión: `run()` no puede pisar el canal de una regla existente.

        `Notification.channel` tiene `set_only_once=1` en Frappe, así que
        reasignarlo sobre un documento ya existente lanza
        `CannotChangeConstantError`. Antes de la corrección, `f7` fallaba en TODOS
        los `bench migrate` de producción (donde las 4 reglas de vencimiento están
        en "Email" con SMTP real) y había que aplicar a mano un bypass de 3 pasos
        después de cada despliegue.
        """
        f7.run()
        objetivo = f7.NOTIFICACIONES[0]["name"]
        frappe.db.set_value("Notification", objetivo, "channel", "Email",
                            update_modified=False)

        f7.run()  # no debe lanzar

        self.assertEqual(
            frappe.db.get_value("Notification", objetivo, "channel"), "Email")
        # Y los destinatarios se siguen reescribiendo desde el código.
        self.assertTrue(frappe.db.count("Notification Recipient", {"parent": objetivo}))

        # Se restaura para no dejar residuo: `set_value` commitea fuera del
        # rollback de IntegrationTestCase.
        frappe.db.set_value("Notification", objetivo, "channel",
                            "System Notification", update_modified=False)

    def test_cubre_los_cinco_doctypes(self):
        """Hay una regla por cada DocType con alerta declarada en f7."""
        f7.run()
        dts = {n["document_type"] for n in self._sgc_notifs()}
        self.assertEqual(
            dts,
            {"Documento Controlado", "Evidencia", "Accion Mejora", "Plan Mejora", "Reunion"},
        )

    def test_run_es_idempotente(self):
        """Re-ejecutar no duplica: sigue habiendo 5 (se actualizan en sitio)."""
        f7.run()
        f7.run()
        self.assertEqual(len(self._sgc_notifs()), 5)
