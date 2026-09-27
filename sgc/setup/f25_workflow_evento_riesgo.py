"""F25 workflow — reporte de eventos de riesgo por cualquier colaborador.

El pliego lo pide así: habilitar el reporte de eventos de riesgo a los
colaboradores y, sobre lo reportado, hacer el análisis y definir el plan de
acción para su corrección. El reporte lo escribe cualquier usuario del sistema
(«Desk User», rol automático de Frappe); lo evalúa y decide la DPGC:

    Reportado -> En evaluacion -> Confirmado (abre la No Conformidad)
                              \\-> Descartado (con motivo)

El análisis y el plan no se duplican aquí: viven en la No Conformidad que abre
la confirmación (análisis de causas #34 y Acciones de mejora).

`allow_self_approval=0` en las decisiones bloquea al owner, pero no a
Administrator ni a quien reporta por otro: la independencia real la impone
`EventoRiesgo._validar_decision`.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f25_workflow_evento_riesgo.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

DPGC = "DPGC"
COLABORADOR = "Desk User"

WF_EVENTO = {
    "name": "Evento Riesgo SGC",
    "document_type": "Evento Riesgo",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        # Mientras nadie lo evalúa, quien lo reportó puede completar su relato.
        ("Reportado", "0", COLABORADOR),
        ("En evaluacion", "0", DPGC),
        ("Confirmado", "0", DPGC),
        ("Descartado", "0", DPGC),
    ],
    "transitions": [
        # Tomarlo en evaluación no decide nada -> self_approval=1.
        ("Reportado", "Evaluar", "En evaluacion", DPGC, 1),
        # Confirmar y descartar son la decisión -> self_approval=0 (default).
        ("En evaluacion", "Confirmar", "Confirmado", DPGC),
        ("En evaluacion", "Descartar", "Descartado", DPGC),
    ],
}


def run():
    frappe.flags.in_patch = True
    _ensure_role(DPGC)
    n = _upsert_workflow(WF_EVENTO)
    frappe.db.commit()
    print("Workflow OK:", n, "[Reportado -> En evaluacion -> Confirmado (abre NC) | Descartado]")
