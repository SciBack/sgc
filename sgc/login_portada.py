# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Métricas agregadas y públicas para la portada de inicio de sesión."""

from datetime import datetime
from zoneinfo import ZoneInfo

import frappe
from frappe.query_builder.functions import Count
from frappe.utils import get_system_timezone, nowdate

_CACHE_KEY = "sgc:login-portada:v1"
_CACHE_TTL = 300
_AE_ACTIVAS = ("Planificada", "En curso", "En revision")


def _pct(numerador, denominador):
    return round(numerador * 100 / denominador) if denominador else None


@frappe.whitelist(allow_guest=True)
def metricas_portada():
    """Devuelve únicamente conteos institucionales agregados, sin PII."""
    cache = frappe.cache
    if payload := cache.get_value(_CACHE_KEY):
        return payload

    programas = frappe.get_all(
        "Programa Sede",
        filters={"estado": "activo"},
        fields=["sede"],
        ignore_permissions=True,
    )
    programas_activos = len(programas)
    sedes = len({programa["sede"] for programa in programas if programa.get("sede")})

    autoevaluaciones_activas = frappe.db.count(
        "Autoevaluacion",
        {"docstatus": 0, "estado": ["in", _AE_ACTIVAS]},
    )
    autoevaluaciones_total = frappe.db.count(
        "Autoevaluacion",
        {"docstatus": ["<", 2]},
    )

    hoy = nowdate()
    evidencias_vigentes = frappe.db.count(
        "Evidencia",
        {"vigencia_hasta": [">=", hoy]},
    )
    evidencia = frappe.qb.DocType("Evidencia")
    evidencias_con_vigencia = (
        frappe.qb.from_(evidencia)
        .select(Count(evidencia.name))
        .where(evidencia.vigencia_hasta.isnotnull())
        .run()[0][0]
    )

    payload = {
        "programas": {
            "activos": programas_activos,
            "sedes": sedes,
        },
        "autoevaluaciones": {
            "activas": autoevaluaciones_activas,
            "total": autoevaluaciones_total,
            "pct": _pct(autoevaluaciones_activas, autoevaluaciones_total),
        },
        "evidencias": {
            "vigentes": evidencias_vigentes,
            "con_vigencia": evidencias_con_vigencia,
            "pct": _pct(evidencias_vigentes, evidencias_con_vigencia),
        },
        "calculado_en": datetime.now(ZoneInfo(get_system_timezone())).isoformat(
            timespec="seconds"
        ),
    }
    cache.set_value(_CACHE_KEY, payload, expires_in_sec=_CACHE_TTL)
    return payload
