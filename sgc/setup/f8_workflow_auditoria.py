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
    "send_email_alert": 0,  # revertido 2026-07-19: dispara attach_print (PDF) por email en CUALQUIER save con transicion pendiente, no solo en transiciones reales -- rompio 70 tests y arriesga flood de correos en prod. Necesita diseno propio (Fase 2, item aparte), no un toggle de 1 linea.
    "states": [
        ("Borrador", "0", "Auditor Interno"),
        ("Aprobado", "0", "DPGC"),
        ("En ejecucion", "0", "Auditor Interno"),
        ("Cerrado", "0", "DPGC"),
    ],
    "transitions": [
        # aprobar/cerrar el programa: control real de DPGC sobre el trabajo del
        # auditor -> self_approval=0 (default). Evita que Auditor+DPGC en la
        # misma persona (H1 caso 2) se autoapruebe el programa.
        ("Borrador", "Aprobar programa", "Aprobado", "DPGC"),
        ("Aprobado", "Iniciar ejecucion", "En ejecucion", "Auditor Interno", 1),  # avance operativo
        ("Aprobado", "Devolver a borrador", "Borrador", "DPGC", 1),  # devuelve, afloja
        ("En ejecucion", "Cerrar programa", "Cerrado", "DPGC"),
    ],
}

# --- Workflow 2: Auditoria ---
WF_AUDITORIA = {
    "name": "Auditoria SGC",
    "document_type": "Auditoria",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,  # revertido 2026-07-19: dispara attach_print (PDF) por email en CUALQUIER save con transicion pendiente, no solo en transiciones reales -- rompio 70 tests y arriesga flood de correos en prod. Necesita diseno propio (Fase 2, item aparte), no un toggle de 1 linea.
    "states": [
        ("Planificada", "0", "Auditor Interno"),
        ("En ejecucion", "0", "Auditor Interno"),
        ("Ejecutada", "0", "Auditor Interno"),
        ("Informe emitido", "0", "Auditor Interno"),
        ("Cerrada", "0", "DPGC"),
    ],
    "transitions": [
        # avance operativo de la propia auditoría (todas el mismo rol
        # ejecutor) -> self_approval=1. El control real de independencia de
        # auditoría (ISO 19011) es el cierre por DPGC, abajo.
        ("Planificada", "Iniciar auditoria", "En ejecucion", "Auditor Interno", 1),
        ("En ejecucion", "Marcar ejecutada", "Ejecutada", "Auditor Interno", 1),
        ("Ejecutada", "Emitir informe", "Informe emitido", "Auditor Interno", 1),
        ("Ejecutada", "Devolver a ejecucion", "En ejecucion", "Auditor Interno", 1),
        # cerrar la auditoría: control real -> self_approval=0 (default).
        # Evita que Auditor+DPGC en la misma persona cierre su propia auditoría.
        ("Informe emitido", "Cerrar auditoria", "Cerrada", "DPGC"),
        ("Informe emitido", "Reabrir", "Ejecutada", "DPGC", 1),  # reapertura, afloja
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
