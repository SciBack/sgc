"""F2 workflow — crea los 2 Workflow nativos del SGC (Autoevaluacion y No Conformidad).

Contrato: F2-CONTRATO.md §4 (agente W). Usa el DocType `Workflow` nativo
(child `states` [state, doc_status, allow_edit] + `transitions`
[state, action, next_state, allowed]). NO reimplementa maquinas de estado.

Idempotente:
- Roles: se crean si no existen (`Responsable de Programa`, `DPGC`).
  `System Manager` ya existe (Frappe core).
- Workflow State (maestro global de Frappe): se crea cada estado si falta.
- Workflow (los 2 registros): se hace upsert (delete+recreate de states/transitions
  si ya existe, para poder reejecutar tras ajustes).

IMPORTANTE — los nombres de estado se ADAPTAN a los valores REALES del Select
`estado` de cada DocType (verificados en los .json), NO a los del contrato:
- Autoevaluacion.estado : Planificada / En curso / En revision / Consolidada / Cerrada
  (el contrato decia Borrador->En evaluacion->En revision->Cerrada; el Select real
   es otro, asi que el workflow sigue el Select real).
- No Conformidad.estado : Abierta / En analisis / En tratamiento / En verificacion /
  Cerrada eficaz / Cerrada no eficaz  (coincide con el contrato).

Ejecutar (lo hace el orquestador, NO este agente):
    bench --site sgc.localhost execute sgc.setup.f2_workflow.run
"""
import frappe

# Roles usados en las transiciones. System Manager ya existe en Frappe core.
ROLES = ["Responsable de Calidad de Programa", "DPGC"]

# --- Workflow 1: Autoevaluacion (estados = Select real de Autoevaluacion.estado) ---
WF_AUTOEVAL = {
    "name": "Autoevaluacion SGC",
    "document_type": "Autoevaluacion",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    # state, doc_status, allow_edit (rol que puede editar el doc en ese estado)
    "states": [
        ("Planificada", "0", "Responsable de Calidad de Programa"),
        ("En curso", "0", "Responsable de Calidad de Programa"),
        ("En revision", "0", "DPGC"),
        ("Consolidada", "0", "DPGC"),
        ("Cerrada", "0", "DPGC"),
    ],
    # state (desde), action (boton), next_state (hacia), allowed (rol)
    "transitions": [
        ("Planificada", "Iniciar evaluacion", "En curso", "Responsable de Calidad de Programa"),
        ("En curso", "Enviar a revision", "En revision", "Responsable de Calidad de Programa"),
        ("En revision", "Devolver a evaluacion", "En curso", "DPGC"),
        ("En revision", "Consolidar", "Consolidada", "DPGC"),
        ("Consolidada", "Cerrar", "Cerrada", "DPGC"),
    ],
}

# --- Workflow 2: No Conformidad (estados = Select real de No Conformidad.estado) ---
WF_NC = {
    "name": "No Conformidad SGC",
    "document_type": "No Conformidad",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        ("Abierta", "0", "Responsable de Calidad de Programa"),
        ("En analisis", "0", "Responsable de Calidad de Programa"),
        ("En tratamiento", "0", "Responsable de Calidad de Programa"),
        ("En verificacion", "0", "DPGC"),
        ("Cerrada eficaz", "0", "DPGC"),
        ("Cerrada no eficaz", "0", "DPGC"),
    ],
    "transitions": [
        ("Abierta", "Analizar causa", "En analisis", "Responsable de Calidad de Programa"),
        ("En analisis", "Tratar", "En tratamiento", "Responsable de Calidad de Programa"),
        ("En tratamiento", "Enviar a verificacion", "En verificacion", "Responsable de Calidad de Programa"),
        ("En verificacion", "Cerrar eficaz", "Cerrada eficaz", "DPGC"),
        ("En verificacion", "Cerrar no eficaz", "Cerrada no eficaz", "DPGC"),
        ("En verificacion", "Reabrir tratamiento", "En tratamiento", "DPGC"),
    ],
}


def _ensure_role(role_name):
    """Crea un Role si no existe. Idempotente."""
    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": 1,
        }).insert(ignore_permissions=True)


def _ensure_workflow_state(state_name, style="Primary"):
    """Crea el maestro global `Workflow State` si no existe. Idempotente.
    (Frappe exige que cada estado usado en un Workflow exista como Workflow State.)
    """
    if not frappe.db.exists("Workflow State", state_name):
        frappe.get_doc({
            "doctype": "Workflow State",
            "workflow_state_name": state_name,
            "style": style,
        }).insert(ignore_permissions=True)


def _ensure_workflow_action(action_name):
    """Crea el maestro global `Workflow Action Master` si no existe. Idempotente."""
    if not frappe.db.exists("Workflow Action Master", action_name):
        frappe.get_doc({
            "doctype": "Workflow Action Master",
            "workflow_action_name": action_name,
        }).insert(ignore_permissions=True)


def _upsert_workflow(spec):
    """Crea o actualiza un Workflow nativo con sus states y transitions."""
    # 1) asegurar los maestros globales de estados y acciones
    for state, _docstatus, _allow_edit in spec["states"]:
        _ensure_workflow_state(state)
    for _from, action, _to, _allowed in spec["transitions"]:
        _ensure_workflow_action(action)

    # 2) upsert del Workflow
    if frappe.db.exists("Workflow", spec["name"]):
        doc = frappe.get_doc("Workflow", spec["name"])
        doc.set("states", [])
        doc.set("transitions", [])
    else:
        doc = frappe.new_doc("Workflow")
        doc.workflow_name = spec["name"]

    doc.document_type = spec["document_type"]
    doc.workflow_state_field = spec["workflow_state_field"]
    doc.is_active = spec["is_active"]
    doc.send_email_alert = spec["send_email_alert"]

    for state, docstatus, allow_edit in spec["states"]:
        doc.append("states", {
            "state": state,
            "doc_status": docstatus,
            "allow_edit": allow_edit,
        })

    for from_state, action, next_state, allowed in spec["transitions"]:
        doc.append("transitions", {
            "state": from_state,
            "action": action,
            "next_state": next_state,
            "allowed": allowed,
            "allow_self_approval": 1,
        })

    doc.save(ignore_permissions=True)
    return doc.name


def run():
    frappe.flags.in_patch = True

    # 1) roles
    for r in ROLES:
        _ensure_role(r)

    # 2) los 2 workflows
    n_auto = _upsert_workflow(WF_AUTOEVAL)
    n_nc = _upsert_workflow(WF_NC)

    frappe.db.commit()

    print("Roles OK:", ", ".join(ROLES), "(+ System Manager ya existente)")
    print("Workflow OK:", n_auto,
          "[Planificada -> En curso -> En revision -> Consolidada -> Cerrada]")
    print("Workflow OK:", n_nc,
          "[Abierta -> En analisis -> En tratamiento -> En verificacion -> "
          "Cerrada eficaz | Cerrada no eficaz]")
