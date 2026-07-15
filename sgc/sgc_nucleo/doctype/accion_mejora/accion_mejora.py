# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

# Avance implícito por estado: los estados terminales fijan el %. En "En ejecucion"
# y "Verificada no eficaz" se respeta el % manual que registre el responsable.
ESTADO_AVANCE = {
    "Planificada": 0,
    "Ejecutada": 100,
    "Verificada eficaz": 100,
}


class AccionMejora(Document):
    def validate(self):
        if self.estado in ESTADO_AVANCE:
            self.avance_pct = ESTADO_AVANCE[self.estado]
        self.avance_pct = max(0, min(100, int(self.avance_pct or 0)))

    def on_update(self):
        self._recalcular_plan()

    def on_trash(self):
        # on_trash corre ANTES del delete físico: hay que excluir esta acción del
        # recálculo, si no seguiría contando en el promedio del plan.
        self._recalcular_plan(excluir=self.name)

    def _recalcular_plan(self, excluir=None):
        """Propaga el avance/semáforo al plan padre. set_value directo dentro de
        recalcular_avance evita recursión (no re-guarda el plan entero)."""
        if self.plan_mejora and frappe.db.exists("Plan Mejora", self.plan_mejora):
            frappe.get_doc("Plan Mejora", self.plan_mejora).recalcular_avance(
                save=True, excluir_accion=excluir
            )
