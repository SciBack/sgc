# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

# Orden del ciclo de vida (coincide con el Workflow "No Conformidad SGC").
# Se usa para exigir, de forma incremental, lo que cada etapa requiere (RF-B05).
ORDEN = {
    "Abierta": 0,
    "En analisis": 1,
    "En tratamiento": 2,
    "En verificacion": 3,
    "Cerrada eficaz": 4,
    "Cerrada no eficaz": 4,
}


class NoConformidad(Document):
    def validate(self):
        # Una NC mayor siempre exige análisis de causa raíz.
        if self.tipo == "No conformidad mayor":
            self.requiere_analisis_causa = 1

        if not self.fecha_deteccion:
            self.fecha_deteccion = nowdate()

        nivel = ORDEN.get(self.estado, 0)

        # A partir de "En analisis": debe haber un responsable asignado.
        if nivel >= 1 and not self.responsable:
            frappe.throw(_("Asigna un responsable antes de pasar la NC a análisis."))

        # A partir de "En tratamiento": si requiere análisis de causa, debe estar redactado.
        if nivel >= 2 and self.requiere_analisis_causa and not (self.analisis_causa or "").strip():
            frappe.throw(_("Esta NC requiere análisis de causa antes de pasar a tratamiento."))

        # A partir de "En verificacion": plazo comprometido + acción correctiva
        # (un plan de mejora vinculado o, al menos, una corrección inmediata registrada).
        if nivel >= 3:
            if not self.fecha_compromiso:
                frappe.throw(_("Define la fecha de compromiso (plazo) antes de enviar a verificación."))
            if not self.plan_mejora and not (self.correccion_inmediata or "").strip():
                frappe.throw(_("Vincula un plan de mejora o registra una corrección antes de verificar."))

        # Al cerrar: evidencia de cierre + quién verificó.
        if self.estado in ("Cerrada eficaz", "Cerrada no eficaz"):
            if not self.evidencia_cierre:
                frappe.throw(_("Adjunta la evidencia de cierre para cerrar la NC."))
            if not self.verificada_por:
                frappe.throw(_("Registra quién verificó el cierre de la NC."))
