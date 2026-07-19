"""F12 workflow — Workflow nativo de Hallazgo (M08, de autoevaluación).

Fase 2 (2026-07-19, hallazgo H3): `Hallazgo` no tenía workflow — el ciclo CAPA
completo (Abierto→...→Cerrado eficaz) era un Select libre, autoconcedible por
cualquier rol con `write`. Asimetría injustificada con `No Conformidad`, que sí
lo tiene desde F2. Mismo patrón: Responsable de Calidad de Programa ejecuta el
tratamiento; DPGC verifica y cierra (no quien lo trató).

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f12_workflow_hallazgo.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

ROLES = ["Responsable de Calidad de Programa", "DPGC"]

WF_HALLAZGO = {
    "name": "Hallazgo SGC",
    "document_type": "Hallazgo",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        ("Abierto", "0", "Responsable de Calidad de Programa"),
        ("En tratamiento", "0", "Responsable de Calidad de Programa"),
        ("Verificacion", "0", "DPGC"),
        ("Cerrado eficaz", "0", "DPGC"),
        ("Cerrado no eficaz", "0", "DPGC"),
    ],
    "transitions": [
        # avance operativo del propio tratamiento -> self_approval=1
        ("Abierto", "Tratar", "En tratamiento", "Responsable de Calidad de Programa", 1),
        ("En tratamiento", "Enviar a verificacion", "Verificacion", "Responsable de Calidad de Programa", 1),
        # cerrar es el control (verificar eficacia de lo que uno mismo trató):
        # self_approval=0 (default) -> quien trató el hallazgo no puede cerrarlo solo.
        ("Verificacion", "Cerrar eficaz", "Cerrado eficaz", "DPGC"),
        ("Verificacion", "Cerrar no eficaz", "Cerrado no eficaz", "DPGC"),
        ("Verificacion", "Reabrir", "En tratamiento", "DPGC", 1),  # reapertura, afloja
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n_h = _upsert_workflow(WF_HALLAZGO)

    frappe.db.commit()

    print("Workflow OK:", n_h,
          "[Abierto -> En tratamiento -> Verificacion -> "
          "Cerrado eficaz | Cerrado no eficaz]")
