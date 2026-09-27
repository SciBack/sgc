# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Salidas no conformes por proceso y decisión (#33, ISO 9001 §8.7).

Responde a las dos preguntas que el registro suelto no contesta:

- **Dónde se concentran.** Un proceso que acumula salidas no conformes tiene un
  problema de sistema, no de casos; es la señal para escalar a no conformidad.
- **Qué se hace con ellas.** Muchas concesiones en un mismo proceso significan
  que se está aceptando como normal lo que no cumple.

Cada fila es un par proceso-decisión, con el número de salidas, la cantidad
afectada (actas, certificados…), cuántas siguen abiertas y cuántas ya escalaron
a no conformidad. Las que aún no tienen decisión salen como «Sin decidir».

Se consulta con `sgc.reportes.consultar`, que respeta permisos.
"""
from frappe import _

from sgc.reportes import aplicar_opcionales, consultar

SIN_DECIDIR = "Sin decidir"
CERRADA = "Cerrada"


def execute(filters=None):
    filters = filters or {}
    return columnas(), filas(filters)


def columnas():
    return [
        {"fieldname": "proceso", "label": _("Proceso"), "fieldtype": "Link",
         "options": "Proceso", "width": 180},
        {"fieldname": "decision", "label": _("Decisión"), "fieldtype": "Data", "width": 190},
        {"fieldname": "salidas", "label": _("Salidas"), "fieldtype": "Int", "width": 90},
        {"fieldname": "cantidad_afectada", "label": _("Cantidad afectada"), "fieldtype": "Int", "width": 140},
        {"fieldname": "abiertas", "label": _("Abiertas"), "fieldtype": "Int", "width": 95},
        {"fieldname": "cerradas", "label": _("Cerradas"), "fieldtype": "Int", "width": 95},
        {"fieldname": "escaladas", "label": _("Escaladas a NC"), "fieldtype": "Int", "width": 125},
    ]


def _filtros(filters):
    filtros = aplicar_opcionales({}, filters, ("proceso", "origen", "decision"))
    desde, hasta = filters.get("desde"), filters.get("hasta")
    if desde and hasta:
        filtros["fecha_deteccion"] = ["between", [desde, hasta]]
    elif desde:
        filtros["fecha_deteccion"] = [">=", desde]
    elif hasta:
        filtros["fecha_deteccion"] = ["<=", hasta]
    return filtros


def filas(filters):
    registros = consultar(
        "Salida No Conforme",
        _filtros(filters),
        ["name", "proceso", "decision", "estado", "cantidad_afectada", "no_conformidad"],
    )
    grupos = {}
    for r in registros:
        clave = (r.proceso, r.decision or SIN_DECIDIR)
        g = grupos.setdefault(clave, {
            "proceso": clave[0], "decision": clave[1], "salidas": 0,
            "cantidad_afectada": 0, "abiertas": 0, "cerradas": 0, "escaladas": 0,
        })
        g["salidas"] += 1
        g["cantidad_afectada"] += r.cantidad_afectada or 0
        if r.estado == CERRADA:
            g["cerradas"] += 1
        else:
            g["abiertas"] += 1
        if r.no_conformidad:
            g["escaladas"] += 1

    # Primero los procesos con más salidas: es donde hay que mirar.
    return sorted(grupos.values(), key=lambda g: (-g["salidas"], g["proceso"] or "", g["decision"]))
