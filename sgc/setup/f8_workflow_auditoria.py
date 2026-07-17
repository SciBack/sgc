"""F8 workflow — Workflows nativos de M06 (Programa Auditoria y Auditoria).

Mismo patrón que f2_workflow.py / f4_workflow_mejora.py (reutiliza sus helpers).
Los estados son los valores REALES del Select `estado` de cada DocType
(verificados en los .json):
- Programa Auditoria.estado : Borrador / Aprobado / En ejecucion / Cerrado
- Auditoria.estado          : Planificada / En ejecucion / Ejecutada /
                              Informe emitido / Cerrada

Roles (ya existentes en el RBAC del SGC, f3b_rbac.py): "Auditor Interno" ejecuta
las auditorías; "DPGC" aprueba el programa y cierra. Las validaciones por etapa
las aplica el controlador (programa_auditoria.py / auditoria.py); el workflow solo
gobierna las transiciones de estado.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f8_workflow_auditoria.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

ROLES = ["Auditor Interno", "DPGC"]

# --- Workflow 1: Programa Auditoria ---
WF_PROGRAMA = {
    "name": "Programa Auditoria SGC",
    "document_type": "Programa Auditoria",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        ("Borrador", "0", "Auditor Interno"),
        ("Aprobado", "0", "DPGC"),
        ("En ejecucion", "0", "Auditor Interno"),
        ("Cerrado", "0", "DPGC"),
    ],
    "transitions": [
        ("Borrador", "Aprobar programa", "Aprobado", "DPGC"),
        ("Aprobado", "Iniciar ejecucion", "En ejecucion", "Auditor Interno"),
        ("Aprobado", "Devolver a borrador", "Borrador", "DPGC"),
        ("En ejecucion", "Cerrar programa", "Cerrado", "DPGC"),
    ],
}

# --- Workflow 2: Auditoria ---
WF_AUDITORIA = {
    "name": "Auditoria SGC",
    "document_type": "Auditoria",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        ("Planificada", "0", "Auditor Interno"),
        ("En ejecucion", "0", "Auditor Interno"),
        ("Ejecutada", "0", "Auditor Interno"),
        ("Informe emitido", "0", "Auditor Interno"),
        ("Cerrada", "0", "DPGC"),
    ],
    "transitions": [
        ("Planificada", "Iniciar auditoria", "En ejecucion", "Auditor Interno"),
        ("En ejecucion", "Marcar ejecutada", "Ejecutada", "Auditor Interno"),
        ("Ejecutada", "Emitir informe", "Informe emitido", "Auditor Interno"),
        ("Ejecutada", "Devolver a ejecucion", "En ejecucion", "Auditor Interno"),
        ("Informe emitido", "Cerrar auditoria", "Cerrada", "DPGC"),
        ("Informe emitido", "Reabrir", "Ejecutada", "DPGC"),
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n_prog = _upsert_workflow(WF_PROGRAMA)
    n_aud = _upsert_workflow(WF_AUDITORIA)

    frappe.db.commit()

    print("Workflow OK:", n_prog,
          "[Borrador -> Aprobado -> En ejecucion -> Cerrado]")
    print("Workflow OK:", n_aud,
          "[Planificada -> En ejecucion -> Ejecutada -> Informe emitido -> Cerrada]")
