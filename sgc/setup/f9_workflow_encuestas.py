"""F9 workflow — Workflow nativo de Aplicación de Instrumento (M12, encuestas).

Mismo patrón que f2_workflow.py / f4_workflow_mejora.py (reutiliza sus helpers).
El único DocType de M12 con Select `estado` de flujo es `Aplicacion Instrumento`;
los estados son los valores REALES del Select (verificados en el .json):

    Aplicacion Instrumento.estado : Planificada / En campo / Cerrada

El campo de la aplicación (tasa de respuesta, conteo LimeSurvey) y la tabulación
de resultados los calcula el controlador (aplicacion_instrumento.py /
resultado_instrumento.py), no el workflow — este solo gobierna las transiciones
de estado del ciclo de campo.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f9_workflow_encuestas.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

ROLES = ["Responsable de Calidad de Programa", "DPGC"]

WF_APLICACION = {
    "name": "Aplicacion Instrumento SGC",
    "document_type": "Aplicacion Instrumento",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,
    "states": [
        ("Planificada", "0", "Responsable de Calidad de Programa"),
        ("En campo", "0", "Responsable de Calidad de Programa"),
        ("Cerrada", "0", "DPGC"),
    ],
    "transitions": [
        ("Planificada", "Iniciar campo", "En campo", "Responsable de Calidad de Programa"),
        ("En campo", "Devolver a planificada", "Planificada", "DPGC"),
        ("En campo", "Cerrar aplicacion", "Cerrada", "DPGC"),
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n_apl = _upsert_workflow(WF_APLICACION)

    frappe.db.commit()

    print("Workflow OK:", n_apl, "[Planificada -> En campo -> Cerrada]")
