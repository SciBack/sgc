# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Resultados de auditoría: qué se encontró y qué se hizo con ello.

El `Informe Auditoria` ya recuenta los hallazgos por tipo de UNA auditoría. Esto
es lo otro: la vista transversal, para cruzar varias auditorías o un periodo
entero y responder a «qué procesos concentran los hallazgos» y «cuántos se
quedaron sin escalar».

## La columna que importa

`Escaló a NC` es la que convierte el informe en útil. Un hallazgo de tipo no
conformidad que nunca se escaló a `No Conformidad` es un hallazgo que se
documentó y no se trató: el ciclo se quedó a medias y, mirando solo la lista de
hallazgos, parece cerrado.

## Permisos

`Hallazgo Auditoria` no está hoy entre los doctypes con aislamiento por ámbito
(`hooks.py:174`), así que aquí `get_list` y `get_all` darían lo mismo. Se usa
`sgc.reportes.consultar` igualmente: el día que se le añada aislamiento —que es
plausible, porque los hallazgos apuntan a proceso y unidad— este informe no
tendrá que acordarse de cambiar nada.
"""
from frappe import _

from sgc.reportes import aplicar_opcionales, consultar

CAMPOS = [
    "name", "codigo", "auditoria", "tipo", "descripcion", "estado",
    "proceso", "unidad_organica", "criterio_incumplido",
    "genera_nc", "no_conformidad",
]

TIPOS_QUE_DEBEN_ESCALAR = ("No conformidad mayor", "No conformidad menor")
# Orden del gráfico: el del campo `tipo` de Hallazgo Auditoria, de más a menos grave.
ORDEN_TIPOS = (
    "No conformidad mayor", "No conformidad menor", "Observacion",
    "Oportunidad de mejora", "Conformidad", "Fortaleza",
)
SIN_TIPO = "(sin tipo)"


def execute(filters=None):
    filters = filters or {}
    data = filas(filters)
    return columnas(), data, None, _grafico(data), _resumen(data)


def columnas():
    return [
        {"fieldname": "codigo", "label": _("Hallazgo"), "fieldtype": "Link",
         "options": "Hallazgo Auditoria", "width": 140},
        {"fieldname": "auditoria", "label": _("Auditoría"), "fieldtype": "Link",
         "options": "Auditoria", "width": 150},
        {"fieldname": "tipo", "label": _("Tipo"), "fieldtype": "Data", "width": 170},
        {"fieldname": "proceso", "label": _("Proceso"), "fieldtype": "Link",
         "options": "Proceso", "width": 140},
        {"fieldname": "unidad_organica", "label": _("Unidad"), "fieldtype": "Link",
         "options": "Unidad Organica", "width": 150},
        {"fieldname": "criterio_incumplido", "label": _("Criterio"), "fieldtype": "Link",
         "options": "Elemento Marco", "width": 140},
        {"fieldname": "descripcion", "label": _("Descripción"), "fieldtype": "Data", "width": 280},
        {"fieldname": "escalo", "label": _("Escaló a NC"), "fieldtype": "Data", "width": 130},
        {"fieldname": "estado", "label": _("Estado"), "fieldtype": "Data", "width": 130},
    ]


def _escalo(fila):
    """Tres respuestas distintas, y la del medio es la que hay que mirar."""
    if fila.get("no_conformidad"):
        return fila["no_conformidad"]
    if fila.get("tipo") in TIPOS_QUE_DEBEN_ESCALAR:
        return _("PENDIENTE")
    return "—"


def filas(filters):
    condiciones = aplicar_opcionales(
        {}, filters, ["auditoria", "tipo", "estado", "proceso", "unidad_organica"]
    )
    if filters.get("solo_sin_escalar"):
        condiciones["tipo"] = ["in", list(TIPOS_QUE_DEBEN_ESCALAR)]
        condiciones["no_conformidad"] = ["is", "not set"]

    hallazgos = consultar(
        "Hallazgo Auditoria", condiciones, CAMPOS, orden="auditoria asc, tipo asc"
    )

    return [{
        "codigo": h.get("name"),
        "auditoria": h.get("auditoria"),
        "tipo": h.get("tipo"),
        "proceso": h.get("proceso"),
        "unidad_organica": h.get("unidad_organica"),
        "criterio_incumplido": h.get("criterio_incumplido"),
        "descripcion": (h.get("descripcion") or "").strip(),
        "escalo": _escalo(h),
        "estado": h.get("estado"),
    } for h in hallazgos]


def _grafico(data):
    """Hallazgos por tipo, de las mismas filas que la tabla (respeta los filtros)."""
    if not data:
        return None
    cuenta = {}
    for f in data:
        tipo = f.get("tipo") or SIN_TIPO
        cuenta[tipo] = cuenta.get(tipo, 0) + 1
    tipos = [t for t in ORDEN_TIPOS if t in cuenta] + sorted(t for t in cuenta if t not in ORDEN_TIPOS)
    return {
        "data": {
            "labels": [_(t) for t in tipos],
            "datasets": [{"name": _("Hallazgos"), "values": [cuenta[t] for t in tipos]}],
        },
        "type": "bar",
        "colors": ["#5e64ff"],
    }


def _resumen(data):
    """Cuántos hay, cuántos son no conformidades y cuántas se quedaron sin tratar."""
    no_conformidades = sum(1 for f in data if f.get("tipo") in TIPOS_QUE_DEBEN_ESCALAR)
    sin_escalar = sum(1 for f in data if f.get("escalo") == _("PENDIENTE"))
    abiertos = sum(1 for f in data if f.get("estado") == "Abierto")
    return [
        {"label": _("Hallazgos"), "value": len(data), "datatype": "Int"},
        {"label": _("No conformidades"), "value": no_conformidades, "datatype": "Int"},
        {"label": _("No conformidades sin escalar"), "value": sin_escalar, "datatype": "Int",
         "indicator": "Red" if sin_escalar else "Green"},
        {"label": _("Abiertos"), "value": abiertos, "datatype": "Int",
         "indicator": "Blue" if abiertos else "Green"},
    ]
