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

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

from sgc.naming import siguiente_correlativo

# Orden del ciclo de vida (coincide con el Workflow "Programa Auditoria SGC").
ORDEN = {
    "Borrador": 0,
    "Aprobado": 1,
    "En ejecucion": 2,
    "Cerrado": 3,
}




class ProgramaAuditoria(Document):
    def before_insert(self):
        # autoname es `field:codigo`: si el usuario no indicó código, se compone
        # aquí (PGA-{anio}-NNNN) antes de que autoname lo lea.
        if not self.codigo:
            self.codigo = self._generar_codigo()

    def validate(self):
        self._sellar_aprobacion()
        self._validar_requisitos_por_estado()
        self._validar_cierre()

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
        return f"{prefijo}{siguiente_correlativo(existentes):04d}"

    def _sellar_aprobacion(self):
        """Aprobar ES firmar: lo registra quien ejecuta la transición.

        Sin esto, `aprobado_por` era un Link que rellenaba a mano cualquiera con
        permiso de edición — incluido el propio auditor que redactó el programa.
        Comprobado en el recorrido del 2026-08-23: el auditor escribió ahí a un
        tercero, la DPGC aprobó, y el programa quedó registrando como aprobador
        a alguien que no tocó el documento. Un programa de auditoría cuya firma
        de aprobación es tecleable por el auditado no separa nada.

        Es el mismo arreglo que `Documento Controlado._sellar_aprobacion`. Se
        sella al ENTRAR en «Aprobado» —comparando con el estado anterior— para
        que una reaprobación tras devolver a borrador registre a quien aprueba
        esta vez, no al de la ronda anterior.

        `responsable` se queda fuera a propósito: es el Jefe de Auditoría
        Interna a cargo del programa, que no tiene por qué ser quien pulsa
        aprobar. Ese sigue declarándose, y hay validación que lo exige.
        """
        anterior = self.get_doc_before_save()
        if self.estado == "Aprobado" and (not anterior or anterior.estado != "Aprobado"):
            self.aprobado_por = frappe.session.user
            self.fecha_aprobacion = nowdate()

    def _validar_cierre(self):
        """Un programa se cierra cuando sus auditorías han concluido (ISO 19011 cl. 5.6).

        Sin esta regla el programa se cerraba con auditorías todavía en
        «Planificada» —comprobado en el recorrido del 2026-08-23— y el
        diagnóstico anual lo leía como programa cumplido. La auditoría que nunca
        se ejecutó quedaba colgando de un programa cerrado, sin que nada lo
        dijera.

        Concluida significa «Cerrada», el único estado final que tiene hoy una
        auditoría: no existe «Cancelada» en su ciclo de vida. Así que una
        auditoría planificada que se decide no hacer hay que borrarla para poder
        cerrar el programa — burdo, pero preferible a cerrar en falso. Si esto
        estorba en la práctica, lo que falta es un estado «Cancelada» en el 07,
        no aflojar esta regla.
        """
        if self.estado != "Cerrado":
            return

        abiertas = frappe.get_all(
            "Auditoria",
            filters={
                "programa_auditoria": self.name,
                "estado": ["!=", "Cerrada"],
            },
            fields=["name", "estado"],
        )
        if abiertas:
            frappe.throw(
                _("No se puede cerrar el programa: {0} auditoría(s) sin concluir ({1}).").format(
                    len(abiertas),
                    ", ".join(f"{a.name} — {a.estado}" for a in abiertas[:5]),
                ),
                title=_("Auditorías abiertas"),
            )

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
            # `aprobado_por` y `fecha_aprobacion` ya no se validan aquí: los
            # sella `_sellar_aprobacion` con quien ejecuta la transición. Pedirle
            # al usuario que los escriba era justo lo que los hacía inventables.
