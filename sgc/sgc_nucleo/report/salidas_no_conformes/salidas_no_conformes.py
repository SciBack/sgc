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

Con **Detalle** marcado, en vez de agrupar lista cada salida con sus datos, los
del proceso, la fecha y **las personas que intervinieron**: quién la detectó,
quién la trató, quién decidió y quién verificó. Es el registro que pide §8.7.2 d
(la autoridad que decide) puesto en una tabla exportable.

Se consulta con `sgc.reportes.consultar`, que respeta permisos.
"""
from frappe import _

from sgc.reportes import aplicar_opcionales, consultar

SIN_DECIDIR = "Sin decidir"
CERRADA = "Cerrada"


def execute(filters=None):
    filters = filters or {}
    if filters.get("detalle"):
        return columnas_detalle(), filas_detalle(filters)
    return columnas(), filas(filters)


def columnas_detalle():
    persona = {"fieldtype": "Link", "options": "User", "width": 170}
    return [
        {"fieldname": "name", "label": _("Salida no conforme"), "fieldtype": "Link",
         "options": "Salida No Conforme", "width": 150},
        {"fieldname": "titulo", "label": _("Título"), "fieldtype": "Data", "width": 240},
        {"fieldname": "fecha_deteccion", "label": _("Detectada el"), "fieldtype": "Date", "width": 110},
        {"fieldname": "proceso", "label": _("Proceso"), "fieldtype": "Link", "options": "Proceso", "width": 150},
        {"fieldname": "unidad_organica", "label": _("Unidad orgánica"), "fieldtype": "Link",
         "options": "Unidad Organica", "width": 150},
        {"fieldname": "origen", "label": _("Origen"), "fieldtype": "Data", "width": 130},
        {"fieldname": "cantidad_afectada", "label": _("Cantidad afectada"), "fieldtype": "Int", "width": 120},
        {"fieldname": "estado", "label": _("Estado"), "fieldtype": "Data", "width": 120},
        {"fieldname": "decision", "label": _("Decisión"), "fieldtype": "Data", "width": 170},
        {"fieldname": "detectado_por", "label": _("Detectado por"), **persona},
        {"fieldname": "responsable", "label": _("Responsable del tratamiento"), **persona},
        {"fieldname": "autorizado_por", "label": _("Decidido por"), **persona},
        {"fieldname": "verificado_por", "label": _("Verificado por"), **persona},
        {"fieldname": "no_conformidad", "label": _("No conformidad"), "fieldtype": "Link",
         "options": "No Conformidad", "width": 150},
    ]


def filas_detalle(filters):
    campos = [c["fieldname"] for c in columnas_detalle()]
    registros = consultar("Salida No Conforme", _filtros(filters), campos,
                          orden="fecha_deteccion desc, creation desc")
    for r in registros:
        r["decision"] = r.get("decision") or SIN_DECIDIR
    return registros


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
