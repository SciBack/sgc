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

    autoevals = _autoevaluaciones()
    return {
        # Lista (no una sola): el sistema sirve a los 22 programas de la UPeU, no
        # a un solo caso. `programas_total` deja explícito el universo.
        "autoevaluaciones": autoevals,
        "programas_total": frappe.db.count("Programa Sede"),
        "pendientes": pendientes,
        "horizonte_dias": horizonte_dias,
    }


# Estados de Autoevaluacion que cuentan como "trabajo vivo" (no cerrada).
_AE_ACTIVAS = ("Planificada", "En curso", "En revision", "Consolidada")


def _autoevaluaciones(limite=12):
    """Autoevaluaciones vivas (no cerradas), cada una con su avance y el conteo de
    criterios valorados vs. pendientes. El sistema es multi-programa: aquí puede
    haber desde 1 (piloto Enfermería) hasta las 22 de la UPeU."""
    campos = [
        "name", "titulo", "programa_sede", "periodo_academico",
        "marco_normativo", "estado", "avance_pct", "resultado_vigencia",
    ]
    aes = frappe.get_all(
        "Autoevaluacion",
        filters={"estado": ["in", _AE_ACTIVAS]},
        fields=campos,
        order_by="modified desc",
        limit=limite,
    )

    # Cache de criterios valorables por marco (varias AE comparten marco).
    crit_por_marco = {}
    for ae in aes:
        marco = ae["marco_normativo"]
        if marco not in crit_por_marco:
            crit_por_marco[marco] = frappe.db.count(
                "Elemento Marco", {"marco_normativo": marco, "es_valorable": 1}
            )
        total = crit_por_marco[marco]
        valorados = frappe.db.count("Valoracion Criterio", {"autoevaluacion": ae["name"]}) if total else 0
        ae["criterios_total"] = total
        ae["criterios_valorados"] = min(valorados, total)
        ae["criterios_pendientes"] = max(0, total - valorados)
    return aes
