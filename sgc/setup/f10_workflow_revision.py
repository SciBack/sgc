"""F10 workflow — Workflow nativo de la Revisión por la Dirección (rama 4, §9.3).

Mismo patrón que f8_workflow_auditoria.py (reutiliza los helpers de f2_workflow.py).
Los estados son los valores REALES del Select `estado` de Revision Direccion
(verificados en el .json): Planificada / Realizada / Cerrada.

La revisión por la dirección la PRESIDE la DPGC (alta dirección del SGC), así que
todas las transiciones las gobierna el rol "DPGC". Las validaciones por etapa
(entradas §9.3.2 al realizarla, salidas §9.3.3 + acta al cerrarla) las aplica el
controlador (revision_direccion.py); el workflow solo gobierna las transiciones.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f10_workflow_revision.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

ROLES = ["DPGC"]

# --- Workflow: Revision Direccion (estados = Select real de Revision Direccion.estado) ---
WF_REVISION = {
    "name": "Revision Direccion SGC",
    "document_type": "Revision Direccion",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    # state, doc_status, allow_edit (rol que puede editar el doc en ese estado)
    "states": [
        ("Planificada", "0", "DPGC"),
        ("Realizada", "0", "DPGC"),
        ("Cerrada", "0", "DPGC"),
    ],
    # state (desde), action (boton), next_state (hacia), allowed (rol)
    "transitions": [
        ("Planificada", "Realizar revision", "Realizada", "DPGC"),
        ("Realizada", "Devolver a planificada", "Planificada", "DPGC"),
        ("Realizada", "Cerrar revision", "Cerrada", "DPGC"),
        ("Cerrada", "Reabrir revision", "Realizada", "DPGC"),
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n_rev = _upsert_workflow(WF_REVISION)

    frappe.db.commit()

    print("Workflow OK:", n_rev,
          "[Planificada -> Realizada -> Cerrada]  (preside DPGC)")
