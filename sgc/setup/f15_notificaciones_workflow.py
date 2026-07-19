"""F15 notificaciones de workflow — alertas en transiciones REALES de Informe
Cumplimiento (Fase 2, hallazgo H2 continuado: f11 le puso workflow al IAC; esto
le agrega aviso a quien debe actuar en cada transición formal).

Reusa el mecanismo de f7_notificaciones.py (`Notification` nativa de Frappe),
pero con `event="Value Change"` sobre `estado` (el `workflow_state_field` de
TODOS los workflows SGC) en vez de "Days Before"/"New". Frappe evalúa
`get_doc_before_save()` contra el valor actual del campo, así que la regla
dispara SOLO en una transición real -- no en cualquier `save()` -- a
diferencia de `send_email_alert` nativo del Workflow doctype, que revirtió
70 tests (ver f2_workflow.py, f11_workflow_cumplimiento.py: `send_email_alert=0`
siempre). Por eso NO se reimplementa `send_email_alert`: se usa `Notification`
con `Value Change`, que ya resuelve el mismo problema de raíz.

`attach_print` queda SIEMPRE en 0 (explícito, ver `_upsert_notification` en
f7_notificaciones.py): adjuntar el PDF es opt-in manual, no algo que este
script encienda.

Reglas creadas:
  1. "SGC - Informe Cumplimiento aprobado" -- dispara al entrar a "Aprobado"
     (única transición entrante: En revisión -> Aprobado, ver
     f11_workflow_cumplimiento.WF_CUMPLIMIENTO). Avisa a la Autoridad
     Aprobadora: ya puede presentar el informe a SUNEDU.
  2. "SGC - Informe Cumplimiento presentado a SUNEDU" -- dispara al entrar a
     "Presentado a SUNEDU" (única transición entrante: Aprobado -> Presentado
     a SUNEDU). Avisa a DPGC: el acto formal externo ya se ejecutó.

`channel="System Notification"` (no "Email") -- el canónico es agnóstico,
igual que las otras notificaciones del SGC; activar Email es config de
runtime (Email Account), no del código canónico.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f15_notificaciones_workflow.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role
from sgc.setup.f7_notificaciones import _upsert_notification

ROL_APROBADORA = "Autoridad Aprobadora"
ROL_VIGILANCIA = "DPGC"

NOTIFICACIONES = [
    {
        "name": "SGC - Informe Cumplimiento aprobado",
        "document_type": "Informe Cumplimiento",
        "event": "Value Change",
        "value_changed": "estado",
        "condition": 'doc.estado == "Aprobado"',
        "channel": "System Notification",
        "attach_print": 0,  # ver docstring de módulo: nunca se activa aquí
        "subject": (
            "Informe de Cumplimiento {{ doc.name }} ({{ doc.anio }}) fue Aprobado"
        ),
        "message": (
            "<p>El Informe de Cumplimiento <b>{{ doc.name }}</b> del año "
            "<b>{{ doc.anio }}</b> fue <b>Aprobado</b>.</p>"
            "<p>Semáforo: {{ doc.semaforo }}. Ya puede presentarse a SUNEDU.</p>"
        ),
        "recipients": [
            {"receiver_by_role": ROL_APROBADORA},
        ],
    },
    {
        "name": "SGC - Informe Cumplimiento presentado a SUNEDU",
        "document_type": "Informe Cumplimiento",
        "event": "Value Change",
        "value_changed": "estado",
        "condition": 'doc.estado == "Presentado a SUNEDU"',
        "channel": "System Notification",
        "attach_print": 0,  # ver docstring de módulo: nunca se activa aquí
        "subject": (
            "Informe de Cumplimiento {{ doc.name }} ({{ doc.anio }}) fue "
            "Presentado a SUNEDU"
        ),
        "message": (
            "<p>El Informe de Cumplimiento <b>{{ doc.name }}</b> del año "
            "<b>{{ doc.anio }}</b> fue <b>Presentado a SUNEDU</b>"
            "{% if doc.fecha_presentacion %} el {{ doc.fecha_presentacion }}"
            "{% endif %}.</p>"
            "<p>El acto formal externo ya se ejecutó; el ciclo del diagnóstico "
            "anual queda cerrado.</p>"
        ),
        "recipients": [
            {"receiver_by_role": ROL_VIGILANCIA},
        ],
    },
]


def run():
    """Crea/actualiza las 2 Notification de transición del IAC. Idempotente."""
    frappe.flags.in_patch = True

    # Ambos roles ya existen en producción (RBAC + f11), pero asegurarlos aquí
    # hace el módulo ejecutable de forma independiente (p.ej. desde un test).
    _ensure_role(ROL_APROBADORA)
    _ensure_role(ROL_VIGILANCIA)

    resultados = []
    for cfg in NOTIFICACIONES:
        accion = _upsert_notification(cfg)
        resultados.append((cfg["name"], accion))
        print("Notification '{0}' {1}  ({2} Value Change sobre estado, canal System)".format(
            cfg["name"], accion, cfg["document_type"]))

    frappe.db.commit()

    print("F15 notificaciones de workflow OK:", len(resultados), "reglas (Informe Cumplimiento).")
    return {"notificaciones": resultados}
