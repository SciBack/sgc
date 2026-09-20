# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Informe de mejoramiento continuo: por cada acción, de qué nace y cómo va.

Responde a la pregunta que se hace en una revisión por la dirección y que hoy
obliga a abrir documentos de uno en uno: **qué se está haciendo con lo que
encontramos, quién lo tiene y cuánto lleva esperando**.

Cada fila es una acción de mejora con su origen (la no conformidad o el hallazgo
que la provocó), su responsable, su plazo y los días que lleva de retraso.

## Dos decisiones de lectura

**El retraso vacío no es cero.** Una acción sin retraso deja la columna en
blanco, no en 0: un cero se lee como «vence hoy» y un hueco como «no aplica».

**Las acciones sin responsable o sin plazo salen igual, y se ven.** Son las que
más fácilmente se pierden: no generan aviso, no entran en el semáforo del plan y
nadie las reclama. Ocultarlas del informe las haría desaparecer del todo.

## Permisos

Consulta con `sgc.reportes.consultar`, que usa `get_list`. No es un detalle de
estilo: `No Conformidad`, `Hallazgo` y `Plan Mejora` tienen aislamiento por
ámbito (`hooks.py:174`), y un `get_all` aquí enseñaría lo de otros programas en
un fichero exportable.
"""
import frappe
from frappe import _

from sgc.reportes import aplicar_opcionales, consultar, dias_de_retraso

ESTADOS_CERRADOS = ("Verificada eficaz", "Verificada no eficaz")

CAMPOS = [
    "name", "codigo", "descripcion", "tipo", "estado", "responsable",
    "fecha_inicio", "fecha_compromiso", "avance_pct",
    "no_conformidad", "hallazgo", "plan_mejora", "evidencia_cierre",
]


def execute(filters=None):
    filters = filters or {}
    return columnas(), filas(filters)


def columnas():
    return [
        {"fieldname": "codigo", "label": _("Código"), "fieldtype": "Link",
         "options": "Accion Mejora", "width": 130},
        {"fieldname": "origen", "label": _("Nace de"), "fieldtype": "Data", "width": 190},
        {"fieldname": "descripcion", "label": _("Acción"), "fieldtype": "Data", "width": 280},
        {"fieldname": "tipo", "label": _("Tipo"), "fieldtype": "Data", "width": 100},
        {"fieldname": "responsable", "label": _("Responsable"), "fieldtype": "Link",
         "options": "User", "width": 170},
        {"fieldname": "fecha_compromiso", "label": _("Compromiso"), "fieldtype": "Date", "width": 110},
        {"fieldname": "dias_retraso", "label": _("Días de retraso"), "fieldtype": "Int", "width": 120},
        {"fieldname": "avance_pct", "label": _("Avance %"), "fieldtype": "Percent", "width": 95},
        {"fieldname": "estado", "label": _("Estado"), "fieldtype": "Data", "width": 140},
        {"fieldname": "evidencia_cierre", "label": _("Evidencia"), "fieldtype": "Link",
         "options": "Evidencia", "width": 130},
    ]


def _origen(fila):
    """De qué nace la acción, en una frase legible.

    Se prefiere la no conformidad al hallazgo porque es el vínculo formal que
    exige la norma; el plan de mejora es el último recurso, porque agrupa.
    """
    if fila.get("no_conformidad"):
        return "NC · {0}".format(fila["no_conformidad"])
    if fila.get("hallazgo"):
        return "Hallazgo · {0}".format(fila["hallazgo"])
    if fila.get("plan_mejora"):
        return "Plan · {0}".format(fila["plan_mejora"])
    return _("Sin origen declarado")


def filas(filters):
    condiciones = aplicar_opcionales(
        {}, filters, ["tipo", "estado", "responsable", "plan_mejora"]
    )
    if filters.get("solo_pendientes"):
        condiciones["estado"] = ["not in", ESTADOS_CERRADOS]

    acciones = consultar(
        "Accion Mejora", condiciones, CAMPOS, orden="fecha_compromiso asc"
    )

    salida = []
    for a in acciones:
        cerrada = a.get("estado") in ESTADOS_CERRADOS
        salida.append({
            "codigo": a.get("name"),
            "origen": _origen(a),
            "descripcion": (a.get("descripcion") or "").strip(),
            "tipo": a.get("tipo"),
            "responsable": a.get("responsable"),
            "fecha_compromiso": a.get("fecha_compromiso"),
            "dias_retraso": dias_de_retraso(a.get("fecha_compromiso"), cerrada),
            "avance_pct": a.get("avance_pct"),
            "estado": a.get("estado"),
            "evidencia_cierre": a.get("evidencia_cierre"),
        })

    sin_responsable = sum(1 for a in acciones if not a.get("responsable"))
    sin_plazo = sum(1 for a in acciones if not a.get("fecha_compromiso"))
    if sin_responsable or sin_plazo:
        frappe.msgprint(
            _("{0} acción(es) sin responsable y {1} sin fecha de compromiso. "
              "No generan aviso ni entran en el semáforo del plan: se pierden solas.")
            .format(sin_responsable, sin_plazo),
            indicator="orange",
            title=_("Acciones invisibles al control"),
        )
    return salida
