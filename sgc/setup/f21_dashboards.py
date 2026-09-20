"""F21 cuadros de mando — los tres tableros del sistema de gestión (issue #30).

Hasta ahora el SGC acumulaba los datos y no los mostraba agregado en ninguna
parte: quien entraba veía listas de documentos, no el estado del sistema. No
existía ni un `Dashboard Chart` ni un `Number Card` en toda la app.

Se crean tres cuadros con los componentes NATIVOS de Frappe, no con una vista
propia. Motivo: el acceso a un chart o a una tarjeta se deriva del acceso al
DocType que consultan (`dashboard_chart.py:27`, `number_card.py:85`), así que el
aislamiento por permisos sale gratis y no hay que mantenerlo aparte.

## Dos restricciones que no son negociables

**1. Ningún gráfico de tipo Heatmap.** El heatmap consulta con `frappe.get_all`
(`dashboard_chart.py:245`), que ignora permisos por diseño; el resto de gráficos
y las tarjetas usan `frappe.get_list` (`:204`, `number_card.py:157`), que los
aplica. Un heatmap mostraría actividad agregada de ámbitos que el usuario no
puede ver. Hay un test que lo comprueba: si alguien añade uno, falla.

**2. `Tablero Indicadores` no se toca.** Ese DocType es configuración de qué
indicadores mira cada rol, y sigue su propio camino. Estos cuadros son del
sistema de gestión, no del catálogo de indicadores.

## Por qué estos números y no otros

Cada tarjeta responde a una pregunta que alguien se hace de verdad al abrir el
sistema por la mañana: qué tengo abierto, qué se me ha pasado de plazo, qué está
en rojo. Los gráficos responden a la siguiente: de dónde viene.

Los tres cuadros de vencimiento son `type="Custom"` y calculan en
`sgc/dashboards.py`; el resto son `Document Type` con filtros estáticos.
"""
import json

import frappe

# --- Tarjetas -------------------------------------------------------------
# El `label` hace de nombre: `NumberCard.autoname()` copia el label al name
# (`frappe/desk/doctype/number_card/number_card.py:53`). Por eso lleva el prefijo
# "SGC - " — ver `_upsert`.

NUMBER_CARDS = [
    {
        "label": "SGC - No conformidades abiertas",
        "document_type": "No Conformidad",
        "module": "SGC Nucleo",
        "type": "Document Type",
        "function": "Count",
        "filters": [["estado", "not in", ["Cerrada eficaz", "Cerrada no eficaz"]]],
        "color": "#e24c4c",
    },
    {
        "label": "SGC - Acciones de mejora vencidas",
        "document_type": "Accion Mejora",
        "module": "SGC Nucleo",
        "type": "Custom",
        "method": "sgc.dashboards.acciones_vencidas",
        "color": "#e24c4c",
    },
    {
        "label": "SGC - Planes de mejora en rojo",
        "document_type": "Plan Mejora",
        "module": "SGC Nucleo",
        "type": "Document Type",
        "function": "Count",
        "filters": [["semaforo", "=", "Rojo"], ["estado", "!=", "Cerrado"]],
        "color": "#e24c4c",
    },
    {
        "label": "SGC - Documentos por revisar",
        "document_type": "Documento Controlado",
        "module": "SGC Nucleo",
        "type": "Custom",
        "method": "sgc.dashboards.documentos_por_revisar",
        "color": "#f2994a",
    },
    {
        "label": "SGC - Hallazgos de auditoria abiertos",
        "document_type": "Hallazgo Auditoria",
        "module": "SGC Auditoria",
        "type": "Document Type",
        "function": "Count",
        "filters": [["estado", "=", "Abierto"]],
        "color": "#f2994a",
    },
    {
        "label": "SGC - Riesgos altos tras tratamiento",
        "document_type": "Evaluacion Riesgo",
        "module": "SGC Riesgos",
        "type": "Document Type",
        "function": "Count",
        "filters": [["momento", "=", "Residual"], ["nivel", "in", ["Alto", "Extremo"]]],
        "color": "#e24c4c",
    },
    {
        "label": "SGC - Tratamientos de riesgo vencidos",
        "document_type": "Tratamiento Riesgo",
        "module": "SGC Riesgos",
        "type": "Custom",
        "method": "sgc.dashboards.tratamientos_riesgo_vencidos",
        "color": "#e24c4c",
    },
]

# --- Gráficos -------------------------------------------------------------
# Ningún `type` puede ser "Heatmap": ver la cabecera del módulo.

CHARTS = [
    {
        "chart_name": "SGC - No conformidades por origen",
        "document_type": "No Conformidad",
        "module": "SGC Nucleo",
        "chart_type": "Group By",
        "group_by_type": "Count",
        "group_by_based_on": "origen_tipo",
        "type": "Donut",
        "filters": [["estado", "not in", ["Cerrada eficaz", "Cerrada no eficaz"]]],
        "number_of_groups": 0,
    },
    {
        "chart_name": "SGC - Acciones de mejora por estado",
        "document_type": "Accion Mejora",
        "module": "SGC Nucleo",
        "chart_type": "Group By",
        "group_by_type": "Count",
        "group_by_based_on": "estado",
        "type": "Bar",
        "filters": [],
        "number_of_groups": 0,
    },
    {
        "chart_name": "SGC - Hallazgos de auditoría por tipo",
        "document_type": "Hallazgo Auditoria",
        "module": "SGC Auditoria",
        "chart_type": "Group By",
        "group_by_type": "Count",
        "group_by_based_on": "tipo",
        "type": "Donut",
        "filters": [],
        "number_of_groups": 0,
    },
    {
        "chart_name": "SGC - Riesgos por categoría",
        "document_type": "Riesgo",
        "module": "SGC Riesgos",
        "chart_type": "Group By",
        "group_by_type": "Count",
        "group_by_based_on": "categoria",
        "type": "Bar",
        "filters": [["estado", "!=", "Cerrado"]],
        "number_of_groups": 0,
    },
    {
        # Serie temporal: cuántas no conformidades se detectan cada mes. Es la
        # única forma de ver si el sistema mejora o solo acumula.
        "chart_name": "SGC - No conformidades detectadas por mes",
        "document_type": "No Conformidad",
        "module": "SGC Nucleo",
        "chart_type": "Count",
        "based_on": "fecha_deteccion",
        "timeseries": 1,
        "timespan": "Last Year",
        "time_interval": "Monthly",
        "type": "Line",
        "filters": [],
    },
]

TIPOS_PROHIBIDOS = ("Heatmap",)


def _upsert(doctype, name, campos):
    """Crea o actualiza sin duplicar. Devuelve 'creado' o 'actualizado'.

    Para que sea idempotente hay que buscar por el name **que el doctype se va a
    poner a sí mismo**. No se puede imponer: `set_new_name` descarta cualquier
    `doc.name` asignado a mano salvo que el autoname sea `prompt` o `uuid`
    (`frappe/model/naming.py`, `doc.name = None`). Los dos doctypes de aquí lo
    derivan de un campo:

    * `Dashboard Chart` → `autoname: field:chart_name`, así que name == chart_name.
    * `Number Card` → no declara autoname, pero su controlador define
      `autoname()` y copia el `label` (`number_card.py:53`).

    Y hay una trampa detrás: si el name calculado ya existe, `Number Card` **no
    falla, añade un sufijo numérico** (`number_card.py:56`). Buscar por un name
    que no coincida con el label no encuentra nada, crea otra tarjeta y el
    contador crece en cada migrate, en silencio. De ahí la comprobación final:
    más vale romper el despliegue que acumular tarjetas fantasma.
    """
    if frappe.db.exists(doctype, name):
        doc = frappe.get_doc(doctype, name)
        accion = "actualizado"
    else:
        doc = frappe.new_doc(doctype)
        accion = "creado"
    for k, v in campos.items():
        if doc.meta.has_field(k):
            doc.set(k, v)
    doc.flags.ignore_permissions = True
    doc.save()
    if doc.name != name:
        frappe.throw(
            "F21: se esperaba que {0} se llamara «{1}» y Frappe lo ha nombrado «{2}». "
            "Repetir el despliegue duplicaria el cuadro en vez de actualizarlo.".format(
                doctype, name, doc.name
            )
        )
    return accion


def _card_fields(cfg):
    campos = {
        "label": cfg["label"],
        "document_type": cfg["document_type"],
        "module": cfg["module"],
        "type": cfg["type"],
        "color": cfg.get("color"),
        "is_public": 1,
        "show_percentage_stats": 0,
    }
    if cfg["type"] == "Custom":
        campos["method"] = cfg["method"]
    else:
        campos["function"] = cfg["function"]
        campos["filters_json"] = json.dumps(cfg.get("filters", []))
    return campos


def _chart_fields(cfg):
    campos = {
        "chart_name": cfg["chart_name"],
        "document_type": cfg["document_type"],
        "module": cfg["module"],
        "chart_type": cfg["chart_type"],
        "type": cfg["type"],
        "filters_json": json.dumps(cfg.get("filters", [])),
        "is_public": 1,
        "timeseries": cfg.get("timeseries", 0),
    }
    for opcional in ("group_by_type", "group_by_based_on", "based_on",
                     "timespan", "time_interval", "number_of_groups"):
        if opcional in cfg:
            campos[opcional] = cfg[opcional]
    return campos


def run():
    frappe.flags.in_patch = True
    resultados = {"cards": [], "charts": []}

    for cfg in NUMBER_CARDS:
        accion = _upsert("Number Card", cfg["label"], _card_fields(cfg))
        resultados["cards"].append((cfg["label"], accion))

    for cfg in CHARTS:
        if cfg["type"] in TIPOS_PROHIBIDOS:
            # Defensa en profundidad: el test lo impide antes, esto lo impide aquí.
            frappe.throw(
                "F21: el tipo de gráfico {0} consulta con get_all e ignora permisos. "
                "No se admite en los cuadros del SGC.".format(cfg["type"])
            )
        accion = _upsert("Dashboard Chart", cfg["chart_name"], _chart_fields(cfg))
        resultados["charts"].append((cfg["chart_name"], accion))

    frappe.db.commit()

    creadas = sum(1 for _, a in resultados["cards"] if a == "creado")
    creados = sum(1 for _, a in resultados["charts"] if a == "creado")
    print(
        "F21 cuadros de mando OK: {0} tarjetas ({1} nuevas), {2} graficos ({3} nuevos)".format(
            len(resultados["cards"]), creadas, len(resultados["charts"]), creados
        )
    )
    return resultados
