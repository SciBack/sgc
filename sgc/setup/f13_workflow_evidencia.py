"""F13 workflow — Workflow nativo de Evidencia (M09, evidencias de acreditación).

Fase 2 (2026-07-19, hallazgo H2): `Evidencia` no tenía workflow — "Valida" (el
acto de validación de la base probatoria de toda la acreditación) era
autoconcedible por quien la sube. Responsable de Calidad de Programa / Dueño de
Proceso suben la evidencia; DPGC o el staff de Analista de Calidad la valida (no
quien la subió). "Vencida" queda fuera del workflow a propósito: la transiciona
un job programado (Fase 2, pendiente) al pasar `vigencia_hasta`, no una persona.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f13_workflow_evidencia.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

ROLES = ["Responsable de Calidad de Programa", "Dueño de Proceso",
         "Analista de Calidad (DPGC)", "DPGC"]

WF_EVIDENCIA = {
    "name": "Evidencia SGC",
    "document_type": "Evidencia",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        ("Pendiente", "0", "Responsable de Calidad de Programa"),
        ("Valida", "0", "DPGC"),
        ("Observada", "0", "Analista de Calidad (DPGC)"),
        ("Subsanada", "0", "Responsable de Calidad de Programa"),
    ],
    "transitions": [
        # validar/observar es el control (alguien distinto de quien subió revisa
        # la base probatoria) -> self_approval=0 (default).
        ("Pendiente", "Validar", "Valida", "Analista de Calidad (DPGC)"),
        ("Pendiente", "Observar", "Observada", "Analista de Calidad (DPGC)", 1),  # flag liviano, afloja
        # subsanar es el avance operativo de quien subió la evidencia -> self_approval=1
        ("Observada", "Subsanar", "Subsanada", "Responsable de Calidad de Programa", 1),
        ("Observada", "Subsanar", "Subsanada", "Dueño de Proceso", 1),
        ("Subsanada", "Validar", "Valida", "Analista de Calidad (DPGC)"),
        ("Subsanada", "Observar", "Observada", "Analista de Calidad (DPGC)", 1),
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n_ev = _upsert_workflow(WF_EVIDENCIA)

    frappe.db.commit()

    print("Workflow OK:", n_ev,
          "[Pendiente -> Valida | Observada -> Subsanada -> Valida]")
