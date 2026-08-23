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

Y una que no depende del estado: el responsable del proceso auditado no puede
estar en el equipo auditor (`_validar_independencia_real`). El Check
`independiente_del_area` lo marca el propio interesado, así que por sí solo no
prueba nada.
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
        self._validar_independencia_real()

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

    def _validar_independencia_real(self):
        """Nadie audita su propio trabajo (ISO 9001 §9.2.2 c, ISO 19011 cl. 5.5.2).

        Hasta ahora la independencia era un Check que marcaba el propio
        interesado. Comprobado en el recorrido del 2026-08-23: el responsable
        de un proceso creó la auditoría a ESE proceso, se puso a sí mismo como
        auditor líder, marcó su propia casilla de «independiente del área» y el
        sistema le dejó iniciar la ejecución. La casilla es una declaración, no
        una comprobación.

        Aquí no se puede comprobar todo —el sistema no sabe a qué área pertenece
        cada persona—, pero sí el caso más claro y el único que tiene dato:
        quien figura como `responsable` del proceso auditado no puede estar en
        el equipo que lo audita. Lo que no se puede comprobar sigue siendo
        declarado; lo que sí, deja de serlo.

        Se comprueba en cada guardado, no solo al iniciar: si no, bastaría con
        añadirse al equipo después de arrancar.
        """
        if not self.proceso or not self.equipo:
            return

        responsable = frappe.db.get_value("Proceso", self.proceso, "responsable")
        if not responsable:
            return

        if any(m.usuario == responsable for m in self.equipo):
            frappe.throw(
                _("{0} es responsable del proceso auditado ({1}): no puede formar "
                  "parte del equipo que lo audita.").format(responsable, self.proceso),
                title=_("El equipo no es independiente"),
            )
