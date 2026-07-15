"""F7 notificaciones — Reglas de alerta por vencimiento (M17), sin depender de SMTP.

Crea/actualiza (idempotente por nombre) varias `Notification` NATIVAS de Frappe
del tipo `event="Days Before"` (basadas en fecha), con canal
`channel="System Notification"`. Se eligió System Notification a propósito: el
envío por email exige un Email Account configurado (pendiente de la contraseña
que dará Alberto/DTI). La notificación de escritorio (campana + Notification Log)
funciona SIN SMTP y queda lista para conmutar a email cuando se configure la
cuenta: bastará añadir el Email Account y (si se quiere) cambiar el `channel` a
"Email", o duplicar la regla con canal Email.

Reglas creadas (una por vencimiento del SGC):
  1. Documento Controlado — 15 días antes de `fecha_proxima_revision`.
  2. Evidencia          — 15 días antes de `vigencia_hasta`.
  3. Acción de Mejora    — 7 días antes de `fecha_compromiso` (ETA).
  4. Plan de Mejora      — 7 días antes de `fecha_compromiso`.

Cada regla evalúa un `condition` (Python sobre `doc`) que descarta los estados
ya cerrados/obsoletos, para no molestar con lo que ya no requiere acción. Los
destinatarios se resuelven por rol (DPGC, la oficina que vigila el SGC) y, cuando
existe, por el campo de usuario responsable del propio documento.

Cómo funciona el disparo: el scheduler de Frappe (ya habilitado) corre a diario
`frappe.email.doctype.notification...` y dispara cada regla `Days Before` sobre
los documentos cuyo campo de fecha cae exactamente a `days_in_advance` días de
hoy y cumplen el `condition`.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f7_notificaciones.run

NOTA: el envío por EMAIL queda pendiente del Email Account (contraseña
Alberto/DTI). Estas reglas ya notifican en la campana/escritorio sin SMTP.
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role

# Rol transversal de la oficina de calidad que monitorea todos los vencimientos.
ROL_VIGILANCIA = "DPGC"

# Cada dict describe una `Notification` nativa. `recipients` lista filas del
# child `Notification Recipient` (por rol y/o por campo de usuario del doc).
NOTIFICACIONES = [
    {
        "name": "SGC - Documento por revisar",
        "document_type": "Documento Controlado",
        "date_changed": "fecha_proxima_revision",
        "days_in_advance": 15,
        # No tiene sentido alertar sobre documentos ya derogados.
        "condition": 'doc.estado != "Obsoleto"',
        "subject": (
            "Documento controlado {{ doc.name }} debe revisarse el "
            "{{ doc.fecha_proxima_revision }}"
        ),
        "message": (
            "<p>El documento controlado <b>{{ doc.name }}</b> "
            "({{ doc.get(\"titulo\") or doc.tipo_documento }}) tiene su "
            "<b>próxima revisión programada</b> para el "
            "<b>{{ doc.fecha_proxima_revision }}</b>.</p>"
            "<p>Estado actual: {{ doc.estado }}. Coordine la revisión antes de "
            "esa fecha para mantener vigente la Lista Maestra de Documentos.</p>"
        ),
        "recipients": [
            {"receiver_by_role": ROL_VIGILANCIA},
            {"receiver_by_document_field": "elaborado_por"},
        ],
    },
    {
        "name": "SGC - Evidencia por vencer",
        "document_type": "Evidencia",
        "date_changed": "vigencia_hasta",
        "days_in_advance": 15,
        # Si ya está marcada Vencida, la alerta preventiva ya no aporta.
        "condition": 'doc.estado != "Vencida"',
        "subject": (
            "Evidencia {{ doc.name }} vence su vigencia el "
            "{{ doc.vigencia_hasta }}"
        ),
        "message": (
            "<p>La evidencia <b>{{ doc.name }}</b> vence su vigencia el "
            "<b>{{ doc.vigencia_hasta }}</b>.</p>"
            "<p>Estado actual: {{ doc.estado }}. Actualice o reemplace la "
            "evidencia para que el programa no quede con soporte vencido.</p>"
        ),
        "recipients": [
            {"receiver_by_role": ROL_VIGILANCIA},
            {"receiver_by_document_field": "cargado_por"},
        ],
    },
    {
        "name": "SGC - Accion de mejora por vencer",
        "document_type": "Accion Mejora",
        "date_changed": "fecha_compromiso",
        "days_in_advance": 7,
        # Solo interesa lo que sigue abierto: una vez eficaz, se cerró el ciclo.
        "condition": 'doc.estado != "Verificada eficaz"',
        "subject": (
            "Acción de mejora {{ doc.name }} vence (ETA) el "
            "{{ doc.fecha_compromiso }}"
        ),
        "message": (
            "<p>La acción de mejora <b>{{ doc.name }}</b> tiene fecha de "
            "compromiso (ETA) el <b>{{ doc.fecha_compromiso }}</b>.</p>"
            "<p>Estado actual: {{ doc.estado }}. Ejecute o actualice la acción "
            "para no incumplir el plan de mejora.</p>"
        ),
        "recipients": [
            {"receiver_by_role": ROL_VIGILANCIA},
            {"receiver_by_document_field": "responsable"},
        ],
    },
    {
        "name": "SGC - Plan de mejora por vencer",
        "document_type": "Plan Mejora",
        "date_changed": "fecha_compromiso",
        "days_in_advance": 7,
        # Un plan Cerrado ya no necesita recordatorio.
        "condition": 'doc.estado != "Cerrado"',
        "subject": (
            "Plan de mejora {{ doc.name }} vence su compromiso el "
            "{{ doc.fecha_compromiso }}"
        ),
        "message": (
            "<p>El plan de mejora <b>{{ doc.name }}</b> tiene fecha compromiso "
            "el <b>{{ doc.fecha_compromiso }}</b>.</p>"
            "<p>Estado actual: {{ doc.estado }} · Semáforo: {{ doc.semaforo }}. "
            "Revise el avance de sus acciones antes del vencimiento.</p>"
        ),
        "recipients": [
            {"receiver_by_role": ROL_VIGILANCIA},
            {"receiver_by_document_field": "responsable"},
        ],
    },
]


def _upsert_notification(cfg):
    """Crea o actualiza una `Notification` nativa. Idempotente por `name`."""
    if frappe.db.exists("Notification", cfg["name"]):
        n = frappe.get_doc("Notification", cfg["name"])
        accion = "actualizada"
    else:
        n = frappe.new_doc("Notification")
        n.name = cfg["name"]
        accion = "creada"

    n.update({
        "subject": cfg["subject"],
        "document_type": cfg["document_type"],
        "event": "Days Before",
        "date_changed": cfg["date_changed"],
        "days_in_advance": cfg["days_in_advance"],
        "channel": "System Notification",
        "condition": cfg["condition"],
        "message": cfg["message"],
        "enabled": 1,
        "is_standard": 0,
    })

    # Reescribe los destinatarios desde cero para que el upsert sea determinista.
    n.set("recipients", [])
    for rec in cfg["recipients"]:
        n.append("recipients", rec)

    n.flags.ignore_permissions = True
    n.save(ignore_permissions=True)
    return accion


def run():
    """Crea/actualiza las Notification de vencimiento del SGC. Idempotente."""
    frappe.flags.in_patch = True

    # El rol de vigilancia debe existir antes de referenciarlo como destinatario.
    _ensure_role(ROL_VIGILANCIA)

    resultados = []
    for cfg in NOTIFICACIONES:
        accion = _upsert_notification(cfg)
        resultados.append((cfg["name"], accion))
        print("Notification '{0}' {1}  ({2} Days Before {3}d, canal System)".format(
            cfg["name"], accion, cfg["document_type"], cfg["days_in_advance"]))

    frappe.db.commit()

    print("F7 notificaciones OK:", len(resultados), "reglas por vencimiento.")
    print("Envío por EMAIL pendiente del Email Account (SMTP). "
          "Por ahora notifican en la campana/escritorio sin SMTP.")
    return {"notificaciones": resultados}
