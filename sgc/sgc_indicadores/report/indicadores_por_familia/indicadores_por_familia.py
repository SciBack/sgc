# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Indicadores por familia: el estado de cada grupo de indicadores de un vistazo.

Una familia es la categoría del indicador, su marco normativo o su proceso. Por
cada una: cuántos indicadores tiene, cuántos tienen medición y cómo está la
última de cada uno (semáforo). Respeta permisos: cuenta lo que quien lo abre
puede ver.
"""

import frappe
from frappe import _

AGRUPACIONES = {
    "Categoría": "categoria",
    "Marco normativo": "marco_normativo",
    "Proceso": "proceso",
}
SIN_FAMILIA = "(sin asignar)"


def execute(filters=None):
    filters = frappe._dict(filters or {})
    etiqueta = filters.agrupar_por if filters.agrupar_por in AGRUPACIONES else "Categoría"
    campo = AGRUPACIONES[etiqueta]

    indicadores = frappe.get_list("Indicador", fields=["name", campo], limit=0)
    ultimo = _ultima_medicion([i.name for i in indicadores], filters.periodo_academico)

    grupos = {}
    for ind in indicadores:
        familia = ind.get(campo) or SIN_FAMILIA
        g = grupos.setdefault(familia, {"familia": familia, "indicadores": 0, "con_medicion": 0,
                                        "verde": 0, "ambar": 0, "rojo": 0, "sin_medicion": 0})
        g["indicadores"] += 1
        semaforo = ultimo.get(ind.name)
        if semaforo is None:
            g["sin_medicion"] += 1
            continue
        g["con_medicion"] += 1
        if semaforo == "Verde":
            g["verde"] += 1
        elif semaforo == "Ambar":
            g["ambar"] += 1
        elif semaforo == "Rojo":
            g["rojo"] += 1

    data = sorted(grupos.values(), key=lambda g: (g["familia"] == SIN_FAMILIA, g["familia"]))
    for g in data:
        evaluados = g["verde"] + g["ambar"] + g["rojo"]
        g["cumplimiento_pct"] = round(100 * g["verde"] / evaluados, 1) if evaluados else None

    return _columnas(etiqueta), data, None, _grafico(data)


def _ultima_medicion(indicadores, periodo=None):
    """Semáforo de la última medición de cada indicador ('' si no tiene semáforo)."""
    if not indicadores:
        return {}
    filtros = {"indicador": ["in", indicadores]}
    if periodo:
        filtros["periodo_academico"] = periodo
    valores = frappe.get_list(
        "Valor Indicador",
        filters=filtros,
        fields=["indicador", "semaforo"],
        order_by="fecha desc, creation desc",
        limit=0,
    )
    ultimo = {}
    for v in valores:
        ultimo.setdefault(v.indicador, v.semaforo or "")
    return ultimo


def _columnas(etiqueta):
    return [
        {"fieldname": "familia", "label": _(etiqueta), "fieldtype": "Data", "width": 260},
        {"fieldname": "indicadores", "label": _("Indicadores"), "fieldtype": "Int", "width": 110},
        {"fieldname": "con_medicion", "label": _("Con medición"), "fieldtype": "Int", "width": 120},
        {"fieldname": "verde", "label": _("En verde"), "fieldtype": "Int", "width": 100},
        {"fieldname": "ambar", "label": _("En ámbar"), "fieldtype": "Int", "width": 100},
        {"fieldname": "rojo", "label": _("En rojo"), "fieldtype": "Int", "width": 100},
        {"fieldname": "sin_medicion", "label": _("Sin medición"), "fieldtype": "Int", "width": 120},
        {"fieldname": "cumplimiento_pct", "label": _("Cumplimiento (%)"), "fieldtype": "Percent", "width": 140},
    ]


def _grafico(data):
    if not data:
        return None
    return {
        "data": {
            "labels": [g["familia"] for g in data],
            "datasets": [
                {"name": _("En verde"), "values": [g["verde"] for g in data]},
                {"name": _("En ámbar"), "values": [g["ambar"] for g in data]},
                {"name": _("En rojo"), "values": [g["rojo"] for g in data]},
                {"name": _("Sin medición"), "values": [g["sin_medicion"] for g in data]},
            ],
        },
        "type": "bar",
        "barOptions": {"stacked": 1},
        "colors": ["#29cd42", "#ffa00a", "#e24c4c", "#c0c6cc"],
    }
