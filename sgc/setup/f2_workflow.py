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
    "send_email_alert": 0,  # revertido 2026-07-19: dispara attach_print (PDF) por email en CUALQUIER save con transicion pendiente, no solo en transiciones reales -- rompio 70 tests y arriesga flood de correos en prod. Necesita diseno propio (Fase 2, item aparte), no un toggle de 1 linea.
    # state, doc_status, allow_edit (rol que puede editar el doc en ese estado)
    "states": [
        ("Planificada", "0", "Responsable de Calidad de Programa"),
        ("En curso", "0", "Responsable de Calidad de Programa"),
        ("En revision", "0", "DPGC"),
        ("Consolidada", "0", "DPGC"),
        # doc_status "1": la transición "Cerrar" hacia este estado dispara el
        # submit NATIVO de Frappe (docstatus 0->1) porque Autoevaluacion es
        # is_submittable=1 -- ver Autoevaluacion.before_submit (captura el
        # marco_snapshot justo antes) y sgc.scoring (lo lee cuando existe).
        ("Cerrada", "1", "DPGC"),
    ],
    # state (desde), action (boton), next_state (hacia), allowed (rol)
    "transitions": [
        # avance operativo del propio trabajo -> self_approval=1 (no es un control de aprobación)
        ("Planificada", "Iniciar evaluacion", "En curso", "Responsable de Calidad de Programa", 1),
        ("En curso", "Enviar a revision", "En revision", "Responsable de Calidad de Programa", 1),
        ("En revision", "Devolver a evaluacion", "En curso", "DPGC", 1),  # devolución, afloja
        # consolidar/cerrar la autoevaluación es el entregable de acreditación:
        # self_approval=0 (default) -> DPGC no puede consolidar/cerrar la AE que
        # ella misma creó; requiere que otra cuenta con rol DPGC lo haga.
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
    "send_email_alert": 0,  # revertido 2026-07-19: dispara attach_print (PDF) por email en CUALQUIER save con transicion pendiente, no solo en transiciones reales -- rompio 70 tests y arriesga flood de correos en prod. Necesita diseno propio (Fase 2, item aparte), no un toggle de 1 linea.
    "states": [
        ("Abierta", "0", "Responsable de Calidad de Programa"),
        ("En analisis", "0", "Responsable de Calidad de Programa"),
        ("En tratamiento", "0", "Responsable de Calidad de Programa"),
        ("En verificacion", "0", "DPGC"),
        ("Cerrada eficaz", "0", "DPGC"),
        ("Cerrada no eficaz", "0", "DPGC"),
    ],
    "transitions": [
        # avance operativo del propio tratamiento -> self_approval=1
        ("Abierta", "Analizar causa", "En analisis", "Responsable de Calidad de Programa", 1),
        ("En analisis", "Tratar", "En tratamiento", "Responsable de Calidad de Programa", 1),
        ("En tratamiento", "Enviar a verificacion", "En verificacion", "Responsable de Calidad de Programa", 1),
        # cerrar la NC es el control (verificar eficacia de lo que uno mismo trató):
        # self_approval=0 (default) -> quien abrió/trató la NC no puede cerrarla sola.
        ("En verificacion", "Cerrar eficaz", "Cerrada eficaz", "DPGC"),
        ("En verificacion", "Cerrar no eficaz", "Cerrada no eficaz", "DPGC"),
        ("En verificacion", "Reabrir tratamiento", "En tratamiento", "DPGC", 1),  # reapertura, afloja
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
    for t in spec["transitions"]:
        _ensure_workflow_action(t[1])

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

    for t in spec["transitions"]:
        from_state, action, next_state, allowed = t[:4]
        # Fase 1 (2026-07-19, hallazgo H1): antes esto era SIEMPRE 1 para las 43
        # transiciones de los 9 workflows -> allow_self_approval=1 anula la
        # segregación de funciones nativa de Frappe (permite que quien CREÓ el
        # documento ejecute también su propia aprobación/cierre/verificación).
        # Default ahora SEGURO (0): cada spec marca explícitamente con un 5º
        # elemento `1` SOLO las transiciones de avance operativo o devolución/
        # reapertura (que aflojan un control, no lo superan).
        self_approval = t[4] if len(t) > 4 else 0
        doc.append("transitions", {
            "state": from_state,
            "action": action,
            "next_state": next_state,
            "allowed": allowed,
            "allow_self_approval": self_approval,
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
