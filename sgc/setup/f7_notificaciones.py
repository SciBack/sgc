"""F7 notificaciones — Reglas de alerta del SGC: por correo y en la campana.

Crea/actualiza (idempotente por nombre) varias `Notification` NATIVAS de Frappe,
con canal `Email` y además `send_system_notification=1`: el aviso llega al
correo y a la campana del Desk. La campana funciona sin SMTP; el correo sale por
la cuenta de correo del sitio.

**Por qué el canónico puede declarar Email sin escribir a nadie por sorpresa
(#29).** Todo correo de una `Notification` pasa por `sgc.correo.NotificacionSGC`,
que obedece a `Configuracion Correo`: un sitio nuevo nace en modo **Ensayo** y
no envía nada —lo anota en `Registro Correo`— hasta que un administrador lo pasa
a Real, con o sin lista blanca de estreno (#41). Activar el correo es así una
decisión de despliegue, no un cambio de código. Hasta #29 el canónico declaraba
`System Notification` y cada institución pasaba las reglas a Email a mano; al
hacerlo perdía la campana, porque `send_system_notification` quedaba en 0.

Reglas creadas:
  1. Documento Controlado — `Days Before`, 15 días antes de `fecha_proxima_revision`.
  2. Evidencia          — `Days Before`, 15 días antes de `vigencia_hasta`.
  3. Acción de Mejora    — `Days Before`, 7 días antes de `fecha_compromiso` (ETA).
  4. Plan de Mejora      — `Days Before`, 7 días antes de `fecha_compromiso`.
  5. Reunion (convocatoria) — `New`, al crear/programar la reunión (no es por
     vencimiento: dispara una sola vez, en el `after_insert`).

Las reglas 1-4 evalúan un `condition` (Python sobre `doc`) que descarta los
estados ya cerrados/obsoletos, para no molestar con lo que ya no requiere
acción. Sus destinatarios se resuelven por rol (DPGC, la oficina que vigila el
SGC) y, cuando existe, por el campo de usuario responsable del propio
documento. La regla 5 es distinta: notifica a los asistentes convocados, no a
DPGC (no es un vencimiento que la oficina de calidad deba vigilar).

Cómo funciona el disparo:
  - Reglas 1-4 (`Days Before`): el scheduler de Frappe corre a diario
    `trigger_daily_alerts` y dispara la regla sobre los documentos cuyo campo de
    fecha cae EXACTAMENTE a `days_in_advance` días de hoy y cumplen el
    `condition`. Un documento coincide un solo día, así que el aviso sale una
    vez. Si el scheduler se para, no sale ninguno: lo vigila `sgc.latido` (#42).
  - Regla 5 (`New`): Frappe la dispara sola, dentro del propio request de
    `doc.insert()` (`Document.run_notifications` mapea el hook `after_insert`
    al evento `New`) — no depende del scheduler.

Las reglas de TRANSICIÓN de estado viven en `f15_notificaciones_workflow.py` y
reutilizan `_upsert_notification`.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f7_notificaciones.run
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
    {
        "name": "SGC - Convocatoria de reunion",
        "document_type": "Reunion",
        # A diferencia de las 4 reglas anteriores, esta no es por vencimiento:
        # dispara una vez al crear la Reunion (after_insert -> evento "New").
        "event": "New",
        "subject": (
            "Convocatoria a reunión {{ doc.name }} del comité {{ doc.comite }}"
            " el {{ doc.fecha }}"
        ),
        "message": (
            "<p>Ha sido convocado a la reunión <b>{{ doc.name }}</b>"
            "{% if doc.titulo %} — {{ doc.titulo }}{% endif %} del comité "
            "<b>{{ doc.comite }}</b>.</p>"
            "<p>Fecha: <b>{{ doc.fecha }}</b>. Modalidad: "
            "{{ doc.modalidad or \"No especificada\" }}.</p>"
            "{% if doc.agenda %}<p>Agenda:</p>{{ doc.agenda }}{% endif %}"
        ),
        # Reunion no tiene workflow (states=[]) ni un campo "responsable"
        # único: la lista de destinatarios es su child table `asistentes`
        # (Reunion Asistente.usuario). No se notifica a DPGC aquí porque no
        # es un vencimiento que la oficina de calidad deba vigilar.
        "recipients": [
            {"receiver_by_document_field": "usuario,asistentes"},
        ],
    },
]


def _upsert_notification(cfg):
    """Crea o actualiza una `Notification` nativa. Idempotente por `name`.

    Soporta 3 `event`: "Days Before"/"Days After" (vencimiento, usa
    date_changed/days_in_advance), "New" (dispara una vez al crear, ver regla
    Reunion) y "Value Change" (dispara al cambiar `cfg["value_changed"]`,
    evaluado por Frappe contra `get_doc_before_save()` -- ver
    f15_notificaciones_workflow.py, notificaciones de transición de workflow).
    """
    if frappe.db.exists("Notification", cfg["name"]):
        n = frappe.get_doc("Notification", cfg["name"])
        accion = "actualizada"
    else:
        n = frappe.new_doc("Notification")
        n.name = cfg["name"]
        accion = "creada"

    event = cfg.get("event", "Days Before")
    campos = {
        "subject": cfg["subject"],
        "document_type": cfg["document_type"],
        "event": event,
        "condition": cfg.get("condition"),
        "message": cfg["message"],
        "enabled": 1,
        "is_standard": 0,
        # Explícito y reescrito en cada upsert (nunca opt-in por defecto):
        # adjuntar el PDF a la notificación es una decisión aparte, no algo
        # que un script de setup declarativo deba encender solo.
        "attach_print": cfg.get("attach_print", 0),
        # Adjuntar un fichero del propio documento (p.ej. el `archivo` de un
        # Documento Controlado al publicarse). Vacío = nada.
        "attach_files": cfg.get("attach_files", ""),
        "from_attach_field": cfg.get("from_attach_field"),
        # La campana del Desk, además del canal. Sin esto, pasar una regla a
        # Email la quitaba de la campana (así quedaron las 4 de UPeU en julio).
        "send_system_notification": cfg.get("send_system_notification", 1),
    }

    # `Notification.channel` tiene set_only_once=1 en Frappe: reasignarlo sobre un
    # documento YA existente lanza CannotChangeConstantError. Por eso el canal solo
    # se fija al CREAR, y al actualizar se respeta el que haya en el sitio. Los
    # sitios anteriores a #29, cuyas reglas nacieron en "System Notification", los
    # pasa a Email una sola vez el parche `notificaciones_por_correo`. Antes de
    # respetar el canal, `f7` fallaba en TODOS los `bench migrate` de producción.
    if accion == "creada":
        campos["channel"] = cfg.get("channel", "Email")

    n.update(campos)
    # date_changed/days_in_advance solo aplican a reglas basadas en fecha
    # (Days Before/After); una regla "New" (p.ej. convocatoria) no los usa.
    if event in ("Days Before", "Days After"):
        n.date_changed = cfg["date_changed"]
        n.days_in_advance = cfg["days_in_advance"]
    # value_changed solo aplica a "Value Change": el campo que Frappe compara
    # contra get_doc_before_save() para decidir si hubo una transición real.
    if event == "Value Change":
        n.value_changed = cfg["value_changed"]

    # Reescribe los destinatarios desde cero para que el upsert sea determinista.
    # Cada fila admite `condition` (Python sobre `doc`): así una sola regla de
    # transición avisa a quien toca según el estado al que se llega.
    n.set("recipients", [])
    for rec in cfg["recipients"]:
        n.append("recipients", rec)

    n.flags.ignore_permissions = True
    n.save(ignore_permissions=True)
    return accion


def run():
    """Crea/actualiza las Notification del SGC (vencimiento + convocatoria). Idempotente."""
    frappe.flags.in_patch = True

    # El rol de vigilancia debe existir antes de referenciarlo como destinatario.
    _ensure_role(ROL_VIGILANCIA)

    resultados = []
    for cfg in NOTIFICACIONES:
        accion = _upsert_notification(cfg)
        resultados.append((cfg["name"], accion))
        event = cfg.get("event", "Days Before")
        if event in ("Days Before", "Days After"):
            detalle = "{0} {1}d".format(event, cfg["days_in_advance"])
        else:
            detalle = event
        print("Notification '{0}' {1}  ({2} {3})".format(
            cfg["name"], accion, cfg["document_type"], detalle))

    frappe.db.commit()

    print("F7 notificaciones OK:", len(resultados), "reglas (vencimiento + convocatoria).")
    return {"notificaciones": resultados}
