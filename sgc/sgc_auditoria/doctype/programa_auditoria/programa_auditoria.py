# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M06 — Programa anual de auditorías internas del SGC.

El programa es el plan de auditorías del periodo (ISO 21001 / ISO 19011 cl. 5,
exigido por SINEACE): define objetivo, alcance y responsable, y se aprueba antes
de ejecutarse. El ciclo de vida lo gobierna el Select `estado`
(Borrador -> Aprobado -> En ejecucion -> Cerrado); las auditorías concretas
cuelgan del programa vía el Link `Auditoria.programa_auditoria`.

Las validaciones son INCREMENTALES por etapa (mismo patrón que M05
No Conformidad): cada estado exige, de forma acumulativa, lo que esa etapa
requiere para no aprobar/ejecutar un programa incompleto.
"""
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

# Orden del ciclo de vida (coincide con el Workflow "Programa Auditoria SGC").
ORDEN = {
    "Borrador": 0,
    "Aprobado": 1,
    "En ejecucion": 2,
    "Cerrado": 3,
}


def _siguiente_correlativo(nombres) -> int:
    """Máximo sufijo numérico de una lista de códigos + 1 (robusto a borrados)."""
    maximo = 0
    for n in nombres:
        m = re.search(r"(\d+)$", n or "")
        if m:
            maximo = max(maximo, int(m.group(1)))
    return maximo + 1


class ProgramaAuditoria(Document):
    def before_insert(self):
        # autoname es `field:codigo`: si el usuario no indicó código, se compone
        # aquí (PGA-{anio}-NNNN) antes de que autoname lo lea.
        if not self.codigo:
            self.codigo = self._generar_codigo()

    def validate(self):
        self._validar_requisitos_por_estado()

    # ---------------------------------------------------------------- helpers
    def _generar_codigo(self) -> str:
        """Código PGA-{anio}-NNNN con correlativo por año (máximo sufijo + 1)."""
        anio = nowdate()[:4]
        prefijo = f"PGA-{anio}-"
        existentes = frappe.get_all(
            "Programa Auditoria",
            filters={"name": ["like", f"{prefijo}%"]},
            pluck="name",
        )
        return f"{prefijo}{_siguiente_correlativo(existentes):04d}"

    # ------------------------------------------------------------ validaciones
    def _validar_requisitos_por_estado(self):
        nivel = ORDEN.get(self.estado, 0)

        # A partir de "Aprobado": debe constar quién aprueba y desde cuándo, y un
        # responsable del programa (Jefe de Auditoría Interna).
        if nivel >= 1:
            if not self.responsable:
                frappe.throw(
                    _("Asigne un responsable del programa antes de aprobarlo.")
                )
            if not self.aprobado_por:
                frappe.throw(
                    _("Indique quién aprueba el programa antes de aprobarlo.")
                )
            # La fecha de aprobación se autocompleta al aprobar si no se indicó.
            if not self.fecha_aprobacion:
                self.fecha_aprobacion = nowdate()
