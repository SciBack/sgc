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
    #
    # EXCEPCIÓN DELIBERADA al default self_approval=0 de f2_workflow._upsert_workflow
    # (Fase 1, 2026-07-19): las 4 transiciones son DPGC y solo DPGC toca este
    # DocType -> si "Realizar revision"/"Cerrar revision" quedaran en 0, DPGC no
    # podría avanzar NINGÚN documento que ella misma creó y el flujo de Revisión
    # por la Dirección (ISO 9001 §9.3) quedaría inejecutable por construcción.
    # Riesgo residual ACEPTADO y documentado (no accidental): la revisión por la
    # dirección hoy se autoaprueba de principio a fin por una sola cuenta DPGC.
    # Mitigación real pendiente de decisión de Alberto: promover "Rectorado/VR
    # (lectura)" a co-aprobador activo de este workflow (dejaría de ser solo
    # lectura). Hasta entonces, self_approval=1 en las 4.
    "transitions": [
        ("Planificada", "Realizar revision", "Realizada", "DPGC", 1),
        ("Realizada", "Devolver a planificada", "Planificada", "DPGC", 1),
        ("Realizada", "Cerrar revision", "Cerrada", "DPGC", 1),
        ("Cerrada", "Reabrir revision", "Realizada", "DPGC", 1),
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
