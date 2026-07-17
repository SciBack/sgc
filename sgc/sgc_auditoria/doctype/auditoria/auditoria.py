# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M06 — Auditoría interna de calidad.

Cada auditoría concreta cuelga (opcionalmente) de un Programa Auditoria y
recorre el ciclo de vida del Select `estado`:

    Planificada -> En ejecucion -> Ejecutada -> Informe emitido -> Cerrada

El código lo genera Frappe de forma nativa (autoname `format:AUD-{YYYY}-{###}`),
así que aquí NO se autogenera.

Validaciones INCREMENTALES por etapa (mismo patrón que M05 No Conformidad):
  En ejecucion  -> exige equipo auditor, criterios y evidencia de independencia
                   (ISO 19011 / ISO 21001 cl. 9.2.2 e); autocompleta fecha_inicio.
  Ejecutada     -> autocompleta fecha_fin.
  Informe emitido -> exige el Informe Auditoria vinculado y que ese informe
                     pertenezca a esta auditoría.
  Cerrada       -> no se cierra una auditoría sin informe emitido.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

# Orden del ciclo de vida (coincide con el Workflow "Auditoria SGC").
ORDEN = {
    "Planificada": 0,
    "En ejecucion": 1,
    "Ejecutada": 2,
    "Informe emitido": 3,
    "Cerrada": 4,
}


class Auditoria(Document):
    def validate(self):
        self._validar_requisitos_por_estado()

    # ------------------------------------------------------------ validaciones
    def _validar_requisitos_por_estado(self):
        nivel = ORDEN.get(self.estado, 0)

        # A partir de "En ejecucion": equipo auditor + criterios + independencia.
        if nivel >= 1:
            if not self.equipo:
                frappe.throw(
                    _("Defina el equipo auditor antes de iniciar la ejecución.")
                )
            if not self.criterios:
                frappe.throw(
                    _("Defina los criterios de auditoría antes de iniciar la ejecución.")
                )
            # Evidencia de independencia (cl. 9.2.2 e): al menos un miembro del
            # equipo debe ser independiente del área auditada.
            if not any(m.independiente_del_area for m in self.equipo):
                frappe.throw(
                    _("El equipo auditor debe tener al menos un miembro independiente "
                      "del área auditada (evidencia de independencia).")
                )
            if not self.fecha_inicio:
                self.fecha_inicio = nowdate()

        # A partir de "Ejecutada": queda registrada la fecha de fin.
        if nivel >= 2 and not self.fecha_fin:
            self.fecha_fin = nowdate()

        # A partir de "Informe emitido": debe existir el informe vinculado y ser
        # de esta misma auditoría (el informe consolida los hallazgos).
        if nivel >= 3:
            if not self.informe:
                frappe.throw(
                    _("Vincule el informe de auditoría antes de darlo por emitido.")
                )
            informe_auditoria = frappe.db.get_value(
                "Informe Auditoria", self.informe, "auditoria"
            )
            if informe_auditoria != self.name:
                frappe.throw(
                    _("El informe {0} no pertenece a esta auditoría.").format(self.informe)
                )

        # "Cerrada": no se cierra una auditoría sin informe emitido.
        if nivel >= 4 and not self.informe:
            frappe.throw(_("No se puede cerrar una auditoría sin informe emitido."))
