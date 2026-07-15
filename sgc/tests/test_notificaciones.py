# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.setup.f7_notificaciones` — reglas de alerta por vencimiento (M17).

Cubre que `run()`:
- Crea las 4 Notification de vencimiento (Documento Controlado, Evidencia,
  Accion Mejora, Plan Mejora) con event="Days Before", canal System y enabled.
- Es idempotente (re-ejecutar no duplica: actualiza en sitio).
"""

import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f7_notificaciones as f7


class IntegrationTestNotificaciones(IntegrationTestCase):
    def _sgc_notifs(self):
        return frappe.get_all(
            "Notification",
            filters={"name": ["like", "SGC%"]},
            fields=["name", "document_type", "event", "date_changed", "channel", "enabled"],
        )

    def test_run_crea_las_cuatro_reglas(self):
        """run() deja 4 Notification 'SGC …' de tipo Days Before, canal System, activas."""
        f7.run()
        notifs = self._sgc_notifs()
        self.assertEqual(len(notifs), 4)
        for n in notifs:
            self.assertEqual(n["event"], "Days Before")
            self.assertEqual(n["channel"], "System Notification")
            self.assertEqual(n["enabled"], 1)
            self.assertTrue(n["date_changed"])  # el campo fecha a vigilar

    def test_cubre_los_cuatro_doctypes(self):
        """Hay una regla por cada DocType con fecha de vencimiento del SGC."""
        f7.run()
        dts = {n["document_type"] for n in self._sgc_notifs()}
        self.assertEqual(
            dts, {"Documento Controlado", "Evidencia", "Accion Mejora", "Plan Mejora"}
        )

    def test_run_es_idempotente(self):
        """Re-ejecutar no duplica: sigue habiendo 4 (se actualizan en sitio)."""
        f7.run()
        f7.run()
        self.assertEqual(len(self._sgc_notifs()), 4)
