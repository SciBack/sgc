# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Matriz de riesgos: de dónde partía cada uno y dónde está tras tratarlo.

El dato que nadie puede ver hoy sin abrir documento por documento es **si el
tratamiento sirvió de algo**: el nivel inherente y el residual viven en filas
distintas de `Evaluacion Riesgo`, y compararlos a ojo en una lista es inviable.

Cada fila de este informe pone los dos niveles juntos y añade la diferencia.

## Las dos señales que el informe hace visibles

**Riesgo alto sin tratamiento.** Un riesgo evaluado como Alto o Extremo para el
que no existe ningún `Tratamiento Riesgo` es un riesgo aceptado sin decirlo. La
columna de estrategia lo muestra vacío.

**Tratamiento que no bajó el nivel.** Cuando el residual iguala o supera al
inherente, el tratamiento no funcionó, y eso es distinto de no haberlo hecho:
obliga a plantear otro, no a repetir el mismo.

## Permisos

`Riesgo` no está hoy entre los doctypes con aislamiento por ámbito
(`hooks.py:174`). Se consulta con `sgc.reportes.consultar` por la misma razón
que el informe de auditoría: para no depender de que alguien se acuerde el día
que eso cambie.
"""
from frappe import _

from sgc.reportes import aplicar_opcionales, consultar

ORDEN_NIVEL = {"Bajo": 1, "Moderado": 2, "Alto": 3, "Extremo": 4}
NIVELES_ALTOS = ("Alto", "Extremo")

CAMPOS_RIESGO = [
    "name", "titulo", "categoria", "estado", "proceso", "unidad_organica",
    "propietario", "matriz_riesgo",
]


def execute(filters=None):
    filters = filters or {}
    data = filas(filters)
    return columnas(), data, None, _grafico(data), _resumen(data)


def columnas():
    return [
        {"fieldname": "riesgo", "label": _("Riesgo"), "fieldtype": "Link",
         "options": "Riesgo", "width": 150},
        {"fieldname": "titulo", "label": _("Título"), "fieldtype": "Data", "width": 260},
        {"fieldname": "categoria", "label": _("Categoría"), "fieldtype": "Data", "width": 130},
        {"fieldname": "proceso", "label": _("Proceso"), "fieldtype": "Link",
         "options": "Proceso", "width": 130},
        {"fieldname": "nivel_inherente", "label": _("Inherente"), "fieldtype": "Data", "width": 105},
        {"fieldname": "nivel_residual", "label": _("Residual"), "fieldtype": "Data", "width": 105},
        {"fieldname": "efecto", "label": _("Efecto del tratamiento"), "fieldtype": "Data", "width": 190},
        {"fieldname": "estrategia", "label": _("Estrategia"), "fieldtype": "Data", "width": 120},
        {"fieldname": "estado_tratamiento", "label": _("Tratamiento"), "fieldtype": "Data", "width": 130},
        {"fieldname": "propietario", "label": _("Propietario"), "fieldtype": "Link",
         "options": "User", "width": 160},
    ]


def _niveles(riesgo):
    """Último nivel inherente y residual del riesgo, por fecha de evaluación."""
    evaluaciones = consultar(
        "Evaluacion Riesgo",
        {"riesgo": riesgo},
        ["momento", "nivel", "fecha"],
        orden="fecha asc",
    )
    niveles = {}
    for e in evaluaciones:
        if e.get("momento") and e.get("nivel"):
            niveles[e["momento"]] = e["nivel"]  # el último gana
    return niveles.get("Inherente"), niveles.get("Residual")


def _tratamiento(riesgo):
    filas_t = consultar(
        "Tratamiento Riesgo",
        {"riesgo": riesgo},
        ["estrategia", "estado", "nivel_residual"],
        orden="modified desc",
    )
    return filas_t[0] if filas_t else None


def _efecto(inherente, residual, hay_tratamiento):
    """Lee los dos niveles y dice, en una frase, si el tratamiento sirvió."""
    if not hay_tratamiento:
        if inherente in NIVELES_ALTOS:
            return _("SIN TRATAMIENTO")
        return "—"
    if not inherente or not residual:
        return _("Sin evaluar")
    antes, despues = ORDEN_NIVEL.get(inherente, 0), ORDEN_NIVEL.get(residual, 0)
    if despues < antes:
        return _("Bajó {0} nivel(es)").format(antes - despues)
    return _("NO BAJÓ")


def filas(filters):
    condiciones = aplicar_opcionales(
        {}, filters, ["categoria", "estado", "proceso", "unidad_organica"]
    )
    riesgos = consultar("Riesgo", condiciones, CAMPOS_RIESGO, orden="categoria asc")

    salida = []
    for r in riesgos:
        inherente, residual = _niveles(r["name"])
        tratamiento = _tratamiento(r["name"])

        if filters.get("solo_altos") and (residual or inherente) not in NIVELES_ALTOS:
            continue

        salida.append({
            "riesgo": r.get("name"),
            "titulo": (r.get("titulo") or "").strip(),
            "categoria": r.get("categoria"),
            "proceso": r.get("proceso"),
            "nivel_inherente": inherente or "—",
            "nivel_residual": residual or "—",
            "efecto": _efecto(inherente, residual, bool(tratamiento)),
            "estrategia": (tratamiento or {}).get("estrategia") or "—",
            "estado_tratamiento": (tratamiento or {}).get("estado") or "—",
            "propietario": r.get("propietario"),
        })
    return salida


def _grafico(data):
    """Cuántos riesgos hay en cada nivel antes y después de tratarlos.

    Sale de las mismas filas que la tabla: con «Solo Alto y Extremo» o un proceso
    elegido, el gráfico cuenta lo mismo que se ve. Los riesgos sin evaluar («—»)
    no tienen nivel y no se pintan.
    """
    if not data:
        return None
    inherente = [sum(1 for f in data if f["nivel_inherente"] == n) for n in ORDEN_NIVEL]
    residual = [sum(1 for f in data if f["nivel_residual"] == n) for n in ORDEN_NIVEL]
    if not any(inherente) and not any(residual):
        return None
    return {
        "data": {
            "labels": [_(n) for n in ORDEN_NIVEL],
            "datasets": [
                {"name": _("Inherente"), "values": inherente},
                {"name": _("Residual"), "values": residual},
            ],
        },
        "type": "bar",
        "colors": ["#ffa00a", "#5e64ff"],
    }


def _resumen(data):
    """Las dos señales del informe, contadas: riesgo alto sin tratar y tratamiento inútil."""
    sin_tratamiento = sum(1 for f in data if f["efecto"] == _("SIN TRATAMIENTO"))
    no_bajo = sum(1 for f in data if f["efecto"] == _("NO BAJÓ"))
    altos = sum(1 for f in data if f["nivel_residual"] in NIVELES_ALTOS
                or (f["nivel_residual"] == "—" and f["nivel_inherente"] in NIVELES_ALTOS))
    return [
        {"label": _("Riesgos"), "value": len(data), "datatype": "Int"},
        {"label": _("En Alto o Extremo hoy"), "value": altos, "datatype": "Int",
         "indicator": "Red" if altos else "Green"},
        {"label": _("Altos sin tratamiento"), "value": sin_tratamiento, "datatype": "Int",
         "indicator": "Red" if sin_tratamiento else "Green"},
        {"label": _("Tratamiento que no bajó el nivel"), "value": no_bajo, "datatype": "Int",
         "indicator": "Red" if no_bajo else "Green"},
    ]
