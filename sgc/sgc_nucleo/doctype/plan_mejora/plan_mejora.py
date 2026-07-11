# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate


class PlanMejora(Document):
    def validate(self):
        # Recalcula en memoria; el save del propio plan persiste los campos.
        self.recalcular_avance(save=False)

    def recalcular_avance(self, save=True):
        """avance_pct = promedio del avance de sus acciones; fecha_compromiso = la
        más tardía; semaforo por vencimiento (RF-C06). Idempotente.

        Se llama desde el propio plan (validate) y desde Accion Mejora cuando una
        acción cambia. Con save=True persiste sin re-disparar validaciones (evita
        recursión plan<->acción)."""
        acciones = frappe.get_all(
            "Accion Mejora",
            filters={"plan_mejora": self.name},
            fields=["avance_pct", "fecha_compromiso", "estado"],
        )
        if acciones:
            avances = [int(a.avance_pct or 0) for a in acciones]
            self.avance_pct = round(sum(avances) / len(acciones))
            fechas = [getdate(a.fecha_compromiso) for a in acciones if a.fecha_compromiso]
            self.fecha_compromiso = max(fechas) if fechas else None
        else:
            self.avance_pct = 0
            self.fecha_compromiso = None
        self.semaforo = self._calcular_semaforo(acciones)

        if save and not self.is_new():
            frappe.db.set_value(
                "Plan Mejora", self.name,
                {
                    "avance_pct": self.avance_pct,
                    "fecha_compromiso": self.fecha_compromiso,
                    "semaforo": self.semaforo,
                },
                update_modified=False,
            )

    def _calcular_semaforo(self, acciones):
        """Rojo: alguna acción abierta ya vencida. Ambar: alguna abierta por vencer
        en <=15 días. Verde: al día o plan cerrado."""
        if self.estado == "Cerrado":
            return "Verde"
        hoy = getdate(nowdate())
        limite_ambar = getdate(add_days(hoy, 15))
        abiertas = [
            a for a in acciones
            if a.estado not in ("Ejecutada", "Verificada eficaz")
        ]
        for a in abiertas:
            if a.fecha_compromiso and getdate(a.fecha_compromiso) < hoy:
                return "Rojo"
        for a in abiertas:
            if a.fecha_compromiso and getdate(a.fecha_compromiso) <= limite_ambar:
                return "Ambar"
        return "Verde"
