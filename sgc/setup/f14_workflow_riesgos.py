"""F14 workflow — Workflows nativos de Riesgo y Tratamiento Riesgo (GRC, M-Riesgos).

Fase 2 (2026-07-19, hallazgo H2): ninguno de los dos tenía workflow. Dueño de
Proceso identifica/evalúa/trata su propio riesgo (avance operativo); DPGC cierra
y confirma la materialización (el paso que puede disparar una No Conformidad vía
`Riesgo.escalar_a_no_conformidad()` — no debe autoconcedérselo quien es dueño del
riesgo). `Tratamiento Riesgo` lo verifica DPGC, no quien lo implementó.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f14_workflow_riesgos.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

ROLES = ["Dueño de Proceso", "DPGC"]

WF_RIESGO = {
    "name": "Riesgo SGC",
    "document_type": "Riesgo",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        ("Identificado", "0", "Dueño de Proceso"),
        ("Evaluado", "0", "Dueño de Proceso"),
        ("En tratamiento", "0", "Dueño de Proceso"),
        ("Monitoreado", "0", "Dueño de Proceso"),
        ("Cerrado", "0", "DPGC"),
        ("Materializado", "0", "DPGC"),
    ],
    "transitions": [
        # avance operativo de la gestión del propio riesgo -> self_approval=1
        ("Identificado", "Evaluar", "Evaluado", "Dueño de Proceso", 1),
        ("Evaluado", "Iniciar tratamiento", "En tratamiento", "Dueño de Proceso", 1),
        ("En tratamiento", "Monitorear", "Monitoreado", "Dueño de Proceso", 1),
        # cerrar y materializar son controles reales -> self_approval=0 (default):
        # materializar dispara potencialmente una NC (escalar_a_no_conformidad), y
        # cerrar confirma que el tratamiento fue efectivo -- ninguno de los dos lo
        # decide en solitario el dueño del riesgo.
        ("Monitoreado", "Cerrar", "Cerrado", "DPGC"),
        ("Monitoreado", "Materializar", "Materializado", "DPGC"),
        ("Materializado", "Cerrar", "Cerrado", "DPGC"),
    ],
}

WF_TRATAMIENTO = {
    "name": "Tratamiento Riesgo SGC",
    "document_type": "Tratamiento Riesgo",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        ("Planificado", "0", "Dueño de Proceso"),
        ("En ejecucion", "0", "Dueño de Proceso"),
        ("Implementado", "0", "Dueño de Proceso"),
        ("Verificado", "0", "DPGC"),
    ],
    "transitions": [
        # avance operativo de la propia implementación -> self_approval=1
        ("Planificado", "Iniciar", "En ejecucion", "Dueño de Proceso", 1),
        ("En ejecucion", "Marcar implementado", "Implementado", "Dueño de Proceso", 1),
        # verificar que el tratamiento fue efectivo: control -> self_approval=0
        # (default). Quien implementó no se autoverifica.
        ("Implementado", "Verificar", "Verificado", "DPGC"),
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n_r = _upsert_workflow(WF_RIESGO)
    n_t = _upsert_workflow(WF_TRATAMIENTO)

    frappe.db.commit()

    print("Workflow OK:", n_r,
          "[Identificado -> Evaluado -> En tratamiento -> Monitoreado -> "
          "Cerrado | Materializado -> Cerrado]")
    print("Workflow OK:", n_t,
          "[Planificado -> En ejecucion -> Implementado -> Verificado]")
