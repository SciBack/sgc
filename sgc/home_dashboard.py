# Copyright (c) 2026, SciBack and Contributors
# For license information, please see license.txt

"""Panel operativo de Inicio del SGC.

Consolida, para la vista Home de la SPA, lo que el comité de calidad necesita al
entrar: sus pendientes reales (evidencias por vencer/vencidas, no conformidades
abiertas, planes/acciones en riesgo, documentos por revisar) y el estado de la
autoevaluación activa (avance, criterios sin valorar, vigencia propuesta).

Es la fuente de verdad del tablero de Inicio: la SPA solo renderiza el payload.
Todo son consultas por estado/fecha (nada hardcodeado). Los umbrales de "próximo
a vencer" se controlan con `horizonte_dias`.
"""

import frappe
from frappe.utils import add_days, nowdate

# Estados terminales / activos por doctype (nombres exactos de los .json).
_NC_CERRADAS = ("Cerrada eficaz", "Cerrada no eficaz")
_EVIDENCIA_ACTIVAS = ("Pendiente", "Valida")
_ACCION_ABIERTAS = ("Planificada", "En ejecucion")


def _cnt(doctype, filtros):
    return frappe.db.count(doctype, filtros)


@frappe.whitelist()
def resumen_inicio(horizonte_dias=30):
    """Payload del tablero de Inicio. Ver docstring del módulo.

    Estructura::

        {
          "autoevaluacion": {name, titulo, marco_normativo, estado, avance_pct,
                             resultado_vigencia, criterios_total,
                             criterios_valorados, criterios_pendientes} | None,
          "pendientes": [{clave, label, valor, tono, doctype}, ...],
          "horizonte_dias": int,
        }
    """
    horizonte_dias = int(horizonte_dias or 30)
    hoy = nowdate()
    limite = add_days(hoy, horizonte_dias)

    pendientes = [
        {
            "clave": "evidencias_vencidas",
            "label": "Evidencias vencidas",
            "valor": _cnt("Evidencia", {"estado": "Vencida"}),
            "tono": "rojo",
            "doctype": "Evidencia",
        },
        {
            "clave": "evidencias_por_vencer",
            "label": "Evidencias por vencer",
            "valor": _cnt(
                "Evidencia",
                {"estado": ["in", _EVIDENCIA_ACTIVAS], "vigencia_hasta": ["between", [hoy, limite]]},
            ),
            "tono": "ambar",
            "doctype": "Evidencia",
        },
        {
            "clave": "nc_abiertas",
            "label": "No conformidades abiertas",
            "valor": _cnt("No Conformidad", {"estado": ["not in", _NC_CERRADAS]}),
            "tono": "rojo",
            "doctype": "No Conformidad",
        },
        {
            "clave": "planes_riesgo",
            "label": "Planes de mejora en riesgo",
            "valor": _cnt("Plan Mejora", {"semaforo": "Rojo"}),
            "tono": "rojo",
            "doctype": "Plan Mejora",
        },
        {
            "clave": "acciones_por_vencer",
            "label": "Acciones por vencer",
            "valor": _cnt(
                "Accion Mejora",
                {"estado": ["in", _ACCION_ABIERTAS], "fecha_compromiso": ["between", [hoy, limite]]},
            ),
            "tono": "ambar",
            "doctype": "Accion Mejora",
        },
        {
            "clave": "docs_por_revisar",
            "label": "Documentos por revisar",
            "valor": _cnt(
                "Documento Controlado",
                {"estado": "Publicado", "fecha_proxima_revision": ["between", [hoy, limite]]},
            ),
            "tono": "ambar",
            "doctype": "Documento Controlado",
        },
    ]

    return {
        "autoevaluacion": _autoevaluacion_activa(),
        "pendientes": pendientes,
        "horizonte_dias": horizonte_dias,
    }


def _autoevaluacion_activa():
    """La autoevaluación "En curso" más reciente (o la más reciente si ninguna lo
    está), enriquecida con el conteo de criterios valorados vs. pendientes."""
    campos = ["name", "titulo", "marco_normativo", "estado", "avance_pct", "resultado_vigencia"]
    ae = frappe.get_all(
        "Autoevaluacion", filters={"estado": "En curso"}, fields=campos, order_by="modified desc", limit=1
    )
    if not ae:
        ae = frappe.get_all("Autoevaluacion", fields=campos, order_by="modified desc", limit=1)
    if not ae:
        return None

    autoeval = ae[0]
    criterios = frappe.get_all(
        "Elemento Marco",
        filters={"marco_normativo": autoeval["marco_normativo"], "es_valorable": 1},
        pluck="name",
    )
    valorados = (
        frappe.db.count("Valoracion Criterio", {"autoevaluacion": autoeval["name"]}) if criterios else 0
    )
    autoeval["criterios_total"] = len(criterios)
    autoeval["criterios_valorados"] = min(valorados, len(criterios))
    autoeval["criterios_pendientes"] = max(0, len(criterios) - valorados)
    return autoeval
