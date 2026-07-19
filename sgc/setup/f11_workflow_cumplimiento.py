"""F11 workflow — Workflow nativo del Informe de Cumplimiento (IAC, licenciamiento CBC/SUNEDU).

Fase 2 (2026-07-19, hallazgo H2 crítico del mapa de código): `Informe Cumplimiento`
no tenía workflow — "Aprobado" y "Presentado a SUNEDU" (un hecho externo
irreversible) eran autoconcedibles por cualquier rol con `write`. Mismo patrón que
f5_workflow_documental.py: DPGC redacta/revisa, Autoridad Aprobadora ejecuta el
acto formal externo (aquí, presentar a SUNEDU — análogo a "Publicar" en Documento
Controlado).

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f11_workflow_cumplimiento.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

ROLES = ["DPGC", "Autoridad Aprobadora"]

WF_CUMPLIMIENTO = {
    "name": "Informe Cumplimiento SGC",
    "document_type": "Informe Cumplimiento",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        ("Borrador", "0", "DPGC"),
        ("En revisión", "0", "DPGC"),
        ("Aprobado", "0", "DPGC"),
        ("Presentado a SUNEDU", "0", "DPGC"),
    ],
    "transitions": [
        ("Borrador", "Enviar a revision", "En revisión", "DPGC", 1),  # avance operativo
        # aprobar es el control interno -> self_approval=0 (default)
        ("En revisión", "Aprobar", "Aprobado", "DPGC"),
        ("Aprobado", "Observar", "Borrador", "DPGC", 1),  # devuelve, afloja
        # presentar a SUNEDU es el acto externo irreversible -> self_approval=0
        # (default), ejecutado por la Autoridad Aprobadora (no quien lo redactó).
        ("Aprobado", "Presentar a SUNEDU", "Presentado a SUNEDU", "Autoridad Aprobadora"),
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n_ic = _upsert_workflow(WF_CUMPLIMIENTO)

    frappe.db.commit()

    print("Workflow OK:", n_ic,
          "[Borrador -> En revisión -> Aprobado -> Presentado a SUNEDU]")
