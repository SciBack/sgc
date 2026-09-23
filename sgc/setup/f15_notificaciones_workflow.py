"""F15 notificaciones de workflow — un aviso en cada transición REAL de estado.

Reusa el mecanismo de f7_notificaciones.py (`Notification` nativa de Frappe),
con `event="Value Change"` sobre `estado` (el `workflow_state_field` de TODOS
los workflows SGC). Frappe compara `get_doc_before_save()` con el valor actual,
así que la regla dispara SOLO cuando el estado cambia de verdad —no en cualquier
`save()` ni al insertar (`Document.run_notifications` no evalúa `Value Change`
con `in_insert`)—. Por eso NO se usa `send_email_alert` del Workflow: dispara en
cualquier guardado con transición pendiente, rompió 70 tests y se revirtió
(ver f8_workflow_auditoria.py y demás `send_email_alert=0`).

**Una regla por DocType, un correo por transición (#29).** Cada regla lleva una
fila de destinatarios por estado de llegada, con `condition` sobre `doc.estado`:
avisa a quien tiene que actuar AHORA. Cuando el documento nombra a esa persona
(`responsable`, `verificada_por`, `revisado_por`…) se le escribe a ella; si el
campo está vacío, al rol que actúa en ese paso del workflow. Los destinatarios
salen en un solo correo.

La publicación de un Documento Controlado es la excepción: va en su propia regla
porque adjunta el `archivo` del documento, que es lo que el lector necesita.
Publicar ya exige el archivo (documento_controlado.py), así que nunca va vacío.

Canal `Email` con campana. Qué se envía de verdad lo decide `Configuracion
Correo` (#41): un sitio nuevo está en Ensayo y no escribe a nadie.

Reglas creadas:
  1-2. Informe Cumplimiento — al quedar "Aprobado" (a la Autoridad Aprobadora) y
       "Presentado a SUNEDU" (a DPGC).
  3.   Documento Controlado  — cualquier transición salvo la publicación.
  4.   Documento Controlado  — publicación, con el archivo adjunto.
  5.   No Conformidad        — cualquier transición.
  6.   Accion Mejora         — cualquier transición.
  7.   Auditoria             — cualquier transición.
  8.   Hallazgo Auditoria    — cualquier transición.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f15_notificaciones_workflow.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role
from sgc.setup.f7_notificaciones import _upsert_notification

ROL_APROBADORA = "Autoridad Aprobadora"
ROL_VIGILANCIA = "DPGC"
ROL_DUENO = "Dueño de Proceso"
ROL_CALIDAD_PROGRAMA = "Responsable de Calidad de Programa"
ROL_AUDITOR = "Auditor Interno"

ROLES = [ROL_APROBADORA, ROL_VIGILANCIA, ROL_DUENO, ROL_CALIDAD_PROGRAMA, ROL_AUDITOR]


# --- helpers de declaración ----------------------------------------------------


def _en(*estados):
    """Condición de una fila de destinatarios: el estado al que se llegó."""
    if len(estados) == 1:
        return 'doc.estado == "{0}"'.format(estados[0])
    return "doc.estado in ({0})".format(", ".join('"{0}"'.format(e) for e in estados))


def _a_campo(campo, *estados):
    """La persona que nombra el documento, al llegar a esos estados."""
    return {"receiver_by_document_field": campo, "condition": _en(*estados)}


def _a_rol(rol, *estados):
    return {"receiver_by_role": rol, "condition": _en(*estados)}


def _a_campo_o_rol(campo, rol, *estados):
    """La persona del campo; si el campo está vacío, el rol que actúa en ese paso.

    Un aviso que no llega a nadie no da ningún síntoma: por eso el rol de respaldo.
    """
    return [
        _a_campo(campo, *estados),
        {"receiver_by_role": rol, "condition": "{0} and not doc.{1}".format(_en(*estados), campo)},
    ]


def _mensaje(que_es, que_hacer, titulo=None):
    """Cuerpo común: qué documento, a qué estado llegó, qué toca hacer y el enlace.

    `que_hacer` es {estado: frase}; un estado sin frase solo informa.
    """
    frases = ", ".join('"{0}": "{1}"'.format(e, f) for e, f in que_hacer.items())
    titulo_html = "{{% if doc.{0} %}} — {{{{ doc.{0} }}}}{{% endif %}}".format(titulo) if titulo else ""
    return (
        "{% set que_hacer = {" + frases + "} %}"
        "<p>" + que_es + " <b>{{ doc.name }}</b>" + titulo_html + " pasó al estado "
        "<b>{{ doc.estado }}</b>.</p>"
        "{% if que_hacer.get(doc.estado) %}<p>{{ que_hacer.get(doc.estado) }}</p>{% endif %}"
        '<p><a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}">'
        "Abrir en el SGC</a></p>"
    )


# --- reglas --------------------------------------------------------------------

NOTIFICACIONES = [
    {
        "name": "SGC - Informe Cumplimiento aprobado",
        "document_type": "Informe Cumplimiento",
        "event": "Value Change",
        "value_changed": "estado",
        "condition": 'doc.estado == "Aprobado"',
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
    {
        "name": "SGC - Documento Controlado cambia de estado",
        "document_type": "Documento Controlado",
        "event": "Value Change",
        "value_changed": "estado",
        # La publicación tiene su propia regla (adjunta el archivo).
        "condition": 'doc.estado != "Publicado"',
        "subject": "Documento {{ doc.name }}: {{ doc.estado }}",
        "message": _mensaje(
            "El documento controlado",
            {
                "En revision": "Revíselo y apruébelo u obsérvelo.",
                "Observado": "Atienda las observaciones y devuélvalo a borrador para corregirlo.",
                "Aprobado": "Ya puede publicarse.",
                "Obsoleto": "Dejó de estar vigente.",
            },
            titulo="titulo",
        ),
        "recipients": [
            *_a_campo_o_rol("revisado_por", ROL_VIGILANCIA, "En revision"),
            *_a_campo_o_rol("elaborado_por", ROL_DUENO, "Observado"),
            *_a_campo_o_rol("aprobado_por", ROL_APROBADORA, "Aprobado"),
            _a_campo("elaborado_por", "Obsoleto"),
        ],
    },
    {
        "name": "SGC - Documento Controlado publicado",
        "document_type": "Documento Controlado",
        "event": "Value Change",
        "value_changed": "estado",
        "condition": 'doc.estado == "Publicado"',
        "attach_files": "From Field",
        "from_attach_field": "archivo",
        "subject": "Documento publicado: {{ doc.name }} — {{ doc.titulo }}",
        "message": (
            "<p>Se publicó el documento controlado <b>{{ doc.name }}</b> — "
            "{{ doc.titulo }}"
            "{% if doc.version %}, versión {{ doc.version }}{% endif %}.</p>"
            "<p>Desde hoy es la versión vigente. Va adjunto.</p>"
            '<p><a href="{{ frappe.utils.get_url_to_form(doc.doctype, doc.name) }}">'
            "Abrir en el SGC</a></p>"
        ),
        "recipients": [
            {"receiver_by_document_field": "elaborado_por"},
            {"receiver_by_document_field": "revisado_por"},
            {"receiver_by_document_field": "aprobado_por"},
            {"receiver_by_role": ROL_VIGILANCIA},
        ],
    },
    {
        "name": "SGC - No Conformidad cambia de estado",
        "document_type": "No Conformidad",
        "event": "Value Change",
        "value_changed": "estado",
        "subject": "No conformidad {{ doc.name }}: {{ doc.estado }}",
        "message": _mensaje(
            "La no conformidad",
            {
                "En analisis": "Analice la causa raíz.",
                "En tratamiento": "Ejecute el tratamiento acordado.",
                "En verificacion": "Verifique la eficacia del tratamiento y cierre la no conformidad.",
                "Cerrada no eficaz": "Se cerró como no eficaz: valore si hace falta otra acción.",
            },
            titulo="titulo",
        ),
        "recipients": [
            *_a_campo_o_rol("responsable", ROL_CALIDAD_PROGRAMA, "En analisis", "En tratamiento"),
            *_a_campo_o_rol("verificada_por", ROL_VIGILANCIA, "En verificacion"),
            _a_campo("responsable", "Cerrada eficaz", "Cerrada no eficaz"),
        ],
    },
    {
        "name": "SGC - Accion de mejora cambia de estado",
        "document_type": "Accion Mejora",
        "event": "Value Change",
        "value_changed": "estado",
        "subject": "Acción de mejora {{ doc.name }}: {{ doc.estado }}",
        "message": _mensaje(
            "La acción de mejora",
            {
                "En ejecucion": "Ejecútela antes de su fecha de compromiso.",
                "Ejecutada": "Verifique si fue eficaz.",
                "Verificada no eficaz": "Se verificó como no eficaz: habrá que retomarla.",
            },
        ),
        "recipients": [
            *_a_campo_o_rol("responsable", ROL_CALIDAD_PROGRAMA, "En ejecucion"),
            *_a_campo_o_rol("verificada_por", ROL_VIGILANCIA, "Ejecutada"),
            _a_campo("responsable", "Verificada eficaz", "Verificada no eficaz"),
        ],
    },
    {
        "name": "SGC - Auditoria cambia de estado",
        "document_type": "Auditoria",
        "event": "Value Change",
        "value_changed": "estado",
        "subject": "Auditoría {{ doc.name }}: {{ doc.estado }}",
        "message": _mensaje(
            "La auditoría",
            {
                "Ejecutada": "Emita el informe de auditoría.",
                "Informe emitido": "Revise el informe y cierre la auditoría.",
            },
            titulo="titulo",
        ),
        "recipients": [
            # El equipo auditor es una tabla hija (Equipo Auditoria.usuario).
            {
                "receiver_by_document_field": "usuario,equipo",
                "condition": _en("En ejecucion", "Ejecutada", "Cerrada"),
            },
            {
                "receiver_by_role": ROL_AUDITOR,
                "condition": _en("En ejecucion", "Ejecutada", "Cerrada") + " and not doc.equipo",
            },
            _a_rol(ROL_VIGILANCIA, "Informe emitido"),
        ],
    },
    {
        "name": "SGC - Hallazgo de auditoria cambia de estado",
        "document_type": "Hallazgo Auditoria",
        "event": "Value Change",
        "value_changed": "estado",
        "subject": "Hallazgo de auditoría {{ doc.name }}: {{ doc.estado }}",
        "message": _mensaje(
            "El hallazgo de auditoría",
            {"Escalado a NC": "Se escaló a una no conformidad: gestiónela desde allí."},
        ),
        # Sin campo de persona: el hallazgo pertenece a una auditoría, y Frappe
        # no sigue enlaces para resolver destinatarios.
        "recipients": [
            _a_rol(ROL_VIGILANCIA, "Escalado a NC"),
            _a_rol(ROL_AUDITOR, "Abierto", "Cerrado"),
        ],
    },
]


def run():
    """Crea/actualiza las Notification de transición. Idempotente."""
    frappe.flags.in_patch = True

    # Los roles ya existen en producción (RBAC), pero asegurarlos aquí hace el
    # módulo ejecutable de forma independiente (p.ej. desde un test).
    for rol in ROLES:
        _ensure_role(rol)

    resultados = []
    for cfg in NOTIFICACIONES:
        accion = _upsert_notification(cfg)
        resultados.append((cfg["name"], accion))
        print("Notification '{0}' {1}  ({2}, Value Change sobre estado)".format(
            cfg["name"], accion, cfg["document_type"]))

    frappe.db.commit()

    print("F15 notificaciones de workflow OK:", len(resultados), "reglas de transición.")
    return {"notificaciones": resultados}
