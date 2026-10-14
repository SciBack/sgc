# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Preparación de evidencias: ¿cada elemento de un marco tiene ya con qué sustentarse, y quién responde?

Pensado para preparar el Informe Anual de Cumplimiento (marco «Ejes Temáticos de Autoevaluación del
IAC»): una fila por pantalla o formato del MIAC, con su unidad responsable, la evidencia que pide y
las evidencias que ya tiene vinculadas por Trazabilidad. Sirve igual para las CBC o un modelo de
acreditación: las filas son los elementos hoja del marco elegido.

Estado de cada elemento:
- «Sin evidencias»: nada vinculado.
- «Con evidencias por validar»: hay evidencias, ninguna Válida todavía.
- «Con evidencia válida»: al menos una evidencia Válida.
"""

from collections import defaultdict

import frappe
from frappe import _

SIN, POR_VALIDAR, VALIDA = "Sin evidencias", "Con evidencias por validar", "Con evidencia válida"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.marco_normativo:
		return COLUMNAS, [], _("Elija un marco normativo."), None, []

	elementos = frappe.get_all(
		"Elemento Marco",
		filters={"marco_normativo": filters.marco_normativo},
		fields=["name", "codigo", "denominacion", "unidad_responsable", "unidades_apoyo",
				"evidencia_requerida", "parent_elemento_marco", "is_group", "lft", "rgt"],
		order_by="lft asc",
		limit=0,
	)
	hojas = [e for e in elementos if not e.is_group]
	ejes = _ejes(elementos)
	evidencias = _evidencias_por_elemento([h.name for h in hojas])

	data = []
	for h in hojas:
		n, validas = evidencias.get(h.name, (0, 0))
		estado = VALIDA if validas else POR_VALIDAR if n else SIN
		fila = {
			"elemento": h.name, "eje": _eje_de(h, ejes), "denominacion": h.denominacion,
			"unidad_responsable": h.unidad_responsable,
			"sin_unidad": "" if h.unidad_responsable else (h.unidades_apoyo or "").split("\n")[0][:140],
			"evidencia_requerida": (h.evidencia_requerida or "").replace("\n", " ")[:300],
			"evidencias": n, "validas": validas, "estado": estado,
		}
		if filters.unidad_responsable and h.unidad_responsable != filters.unidad_responsable:
			continue
		if filters.estado and estado != filters.estado:
			continue
		data.append(fila)

	return COLUMNAS, data, None, _grafico(data), _resumen(data)


COLUMNAS = [
	{"fieldname": "elemento", "label": _("Elemento"), "fieldtype": "Link", "options": "Elemento Marco", "width": 120},
	{"fieldname": "eje", "label": _("Eje"), "fieldtype": "Data", "width": 200},
	{"fieldname": "denominacion", "label": _("Pantalla o elemento"), "fieldtype": "Data", "width": 260},
	{"fieldname": "unidad_responsable", "label": _("Unidad responsable"), "fieldtype": "Link", "options": "Unidad Organica", "width": 200},
	{"fieldname": "sin_unidad", "label": _("Responsable sin unidad en el SGC"), "fieldtype": "Data", "width": 180},
	{"fieldname": "evidencias", "label": _("Evidencias"), "fieldtype": "Int", "width": 90},
	{"fieldname": "validas", "label": _("Válidas"), "fieldtype": "Int", "width": 80},
	{"fieldname": "estado", "label": _("Estado"), "fieldtype": "Data", "width": 190},
	{"fieldname": "evidencia_requerida", "label": _("Evidencia requerida"), "fieldtype": "Data", "width": 400},
]


def _ejes(elementos):
	"""Los elementos del primer nivel bajo la raíz: los ejes, estándares o condiciones del marco."""
	raices = {e.name for e in elementos if not e.parent_elemento_marco}
	return [e for e in elementos if e.parent_elemento_marco in raices]


def _eje_de(elemento, ejes):
	for eje in ejes:
		if eje.lft <= elemento.lft and elemento.rgt <= eje.rgt:
			return f"{eje.codigo.rsplit('-', 1)[-1]}. {eje.denominacion}" if eje.codigo else eje.denominacion
	return ""


def _evidencias_por_elemento(elementos):
	"""{elemento: (evidencias distintas vinculadas, de ellas Válidas)}."""
	if not elementos:
		return {}
	trazas = frappe.get_all("Trazabilidad", filters={"elemento_marco": ["in", elementos]},
						   fields=["elemento_marco", "evidencia"], limit=0)
	por_elemento = defaultdict(set)
	for t in trazas:
		if t.evidencia:
			por_elemento[t.elemento_marco].add(t.evidencia)
	todas = {ev for evs in por_elemento.values() for ev in evs}
	validas = set(frappe.get_all("Evidencia", filters={"name": ["in", list(todas)], "estado": "Valida"},
								 pluck="name", limit=0)) if todas else set()
	return {el: (len(evs), len(evs & validas)) for el, evs in por_elemento.items()}


def _grafico(data):
	por_eje = defaultdict(lambda: [0, 0])
	for f in data:
		por_eje[f["eje"]][0] += 1
		por_eje[f["eje"]][1] += 1 if f["estado"] != SIN else 0
	ejes = list(por_eje)
	return {
		"data": {"labels": [e[:30] for e in ejes],
				 "datasets": [{"name": _("Con alguna evidencia (%)"),
							   "values": [round(100 * por_eje[e][1] / por_eje[e][0]) for e in ejes]}]},
		"type": "bar", "colors": ["#2f6f4f"], "axisOptions": {"xIsSeries": 1},
	}


def _resumen(data):
	total = len(data)
	con = sum(1 for f in data if f["estado"] != SIN)
	validos = sum(1 for f in data if f["estado"] == VALIDA)
	sin_resp = sum(1 for f in data if not f["unidad_responsable"])
	return [
		{"value": total, "label": _("Elementos"), "datatype": "Int"},
		{"value": con, "label": _("Con alguna evidencia"), "datatype": "Int", "indicator": "Orange" if con < total else "Green"},
		{"value": validos, "label": _("Con evidencia válida"), "datatype": "Int", "indicator": "Green" if validos == total else "Red"},
		{"value": sin_resp, "label": _("Sin unidad responsable"), "datatype": "Int", "indicator": "Red" if sin_resp else "Green"},
	]
