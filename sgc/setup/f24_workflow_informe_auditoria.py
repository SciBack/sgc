"""F24 workflow — Revisión y aprobación del Informe de auditoría (ISO 19011 §6.5, #37).

El auditor redacta y envía a revisión; la DPGC revisa, aprueba o devuelve, y
distribuye. La independencia de quien aprueba (no lo emitió, no lo creó, no es
del equipo auditor) la impone el CONTROLADOR (`InformeAuditoria._validar_aprobador_independiente`),
porque `allow_self_approval=0` solo compara con `doc.owner` (ver f14).

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f24_workflow_informe_auditoria.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

DPGC = "DPGC"
AUDITOR = "Auditor Interno"

ROLES = [DPGC, AUDITOR]

WF_INFORME_AUDITORIA = {
    "name": "Informe Auditoria SGC",
    "document_type": "Informe Auditoria",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,  # el correo va por f15 (Value Change), ver f14/f15
    "states": [
        ("Borrador", "0", AUDITOR),
        ("En revision", "0", DPGC),
        ("Aprobado", "0", DPGC),
        ("Distribuido", "0", DPGC),
    ],
    "transitions": [
        # emitir es avance del propio auditor -> self_approval=1
        ("Borrador", "Enviar a revision", "En revision", AUDITOR, 1),
        # aprobar es el control -> self_approval=0 (default)
        ("En revision", "Aprobar", "Aprobado", DPGC),
        # devolver afloja un control, no lo supera -> self_approval=1
        ("En revision", "Devolver a borrador", "Borrador", DPGC, 1),
        # distribuir lo ya aprobado es administrativo
        ("Aprobado", "Distribuir", "Distribuido", DPGC, 1),
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n = _upsert_workflow(WF_INFORME_AUDITORIA)

    frappe.db.commit()

    print("Workflow OK:", n,
          "[Borrador -> En revision -> Aprobado -> Distribuido | En revision -> Borrador (devolver)]")
