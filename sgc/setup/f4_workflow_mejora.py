"""F4 workflow — Workflow nativo de Plan de Mejora y Acción de Mejora (M11).

Mismo patrón que f2_workflow.py (reutiliza sus helpers). Los estados son los
valores REALES del Select `estado` de cada DocType (verificados en los .json):
- Plan Mejora.estado   : Borrador / En ejecucion / Cerrado
- Accion Mejora.estado : Planificada / En ejecucion / Ejecutada /
                         Verificada eficaz / Verificada no eficaz

El avance y el semáforo del plan los calcula el controlador (plan_mejora.py /
accion_mejora.py), no el workflow — este solo gobierna las transiciones de estado.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f4_workflow_mejora.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

ROLES = ["Responsable de Calidad de Programa", "DPGC"]

WF_PLAN = {
    "name": "Plan de Mejora SGC",
    "document_type": "Plan Mejora",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        ("Borrador", "0", "Responsable de Calidad de Programa"),
        ("En ejecucion", "0", "Responsable de Calidad de Programa"),
        ("Cerrado", "0", "DPGC"),
    ],
    "transitions": [
        # aprobar y cerrar el plan: control real -> self_approval=0 (default)
        ("Borrador", "Aprobar y ejecutar", "En ejecucion", "DPGC"),
        ("En ejecucion", "Devolver a borrador", "Borrador", "DPGC", 1),  # devolución, afloja
        ("En ejecucion", "Cerrar plan", "Cerrado", "DPGC"),
    ],
}

WF_ACCION = {
    "name": "Accion de Mejora SGC",
    "document_type": "Accion Mejora",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        ("Planificada", "0", "Responsable de Calidad de Programa"),
        ("En ejecucion", "0", "Responsable de Calidad de Programa"),
        ("Ejecutada", "0", "Responsable de Calidad de Programa"),
        ("Verificada eficaz", "0", "DPGC"),
        ("Verificada no eficaz", "0", "DPGC"),
    ],
    "transitions": [
        # avance operativo de la propia acción -> self_approval=1
        ("Planificada", "Iniciar", "En ejecucion", "Responsable de Calidad de Programa", 1),
        ("En ejecucion", "Marcar ejecutada", "Ejecutada", "Responsable de Calidad de Programa", 1),
        # verificar eficacia es el control -> self_approval=0 (default)
        ("Ejecutada", "Verificar eficaz", "Verificada eficaz", "DPGC"),
        ("Ejecutada", "Verificar no eficaz", "Verificada no eficaz", "DPGC"),
        ("Verificada no eficaz", "Reabrir", "En ejecucion", "DPGC", 1),  # reapertura, afloja
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n_plan = _upsert_workflow(WF_PLAN)
    n_accion = _upsert_workflow(WF_ACCION)

    frappe.db.commit()

    print("Workflow OK:", n_plan, "[Borrador -> En ejecucion -> Cerrado]")
    print("Workflow OK:", n_accion,
          "[Planificada -> En ejecucion -> Ejecutada -> "
          "Verificada eficaz | Verificada no eficaz]")
