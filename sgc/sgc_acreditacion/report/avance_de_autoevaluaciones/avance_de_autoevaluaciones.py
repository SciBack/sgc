# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Avance de autoevaluaciones: ¿cuánto lleva cada programa y cuál puede ir ya a la evaluación externa?

El tablero que la dirección de calidad enseña a las escuelas para que vean cuánto les falta: una fila por
autoevaluación (programa y sede), su % de avance, sus criterios logrados / en proceso / no logrados y si ya
alcanzó el umbral para pedir la evaluación externa (`sgc_umbral_evaluacion_externa`, 75 % por defecto).

El avance es el de la autoevaluación (`scoring._calcular_avance_pct`): con evidencias esperadas, el promedio
del % de sus evidencias; sin ellas, los criterios con juicio. Cada usuario ve las autoevaluaciones que puede
leer (p. ej., un responsable de sede, solo las de su sede).
"""

from collections import Counter

import frappe
from frappe import _

from sgc import scoring

ESTADO_CRITERIO = {"Cumple": "logrados", "Cumple parcial": "en_proceso", "No cumple": "no_logrados", "No aplica": "no_aplica"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	condiciones = {}
	for campo in ("marco_normativo", "estado", "programa_sede"):
		if filters.get(campo):
			condiciones[campo] = filters.get(campo)
	aes = frappe.get_list(
		"Autoevaluacion", filters=condiciones,
		fields=["name", "titulo", "programa_sede", "marco_normativo", "estado", "fecha_inicio", "fecha_cierre"],
		order_by="programa_sede asc", limit=0,
	)
	programas = _programas({a.programa_sede for a in aes if a.programa_sede})
	if filters.facultad:
		aes = [a for a in aes if programas.get(a.programa_sede, {}).get("facultad") == filters.facultad]
	if filters.sede:
		aes = [a for a in aes if programas.get(a.programa_sede, {}).get("sede") == filters.sede]

	umbral = scoring.umbrales()["evaluacion_externa"]
	juicios = _juicios({a.name for a in aes})
	data = []
	for a in aes:
		p = programas.get(a.programa_sede, {})
		c = juicios.get(a.name, Counter())
		avance = scoring._calcular_avance_pct(a.name) if a.estado != "Planificada" else 0.0
		data.append({
			"autoevaluacion": a.name, "programa": p.get("nombre") or a.programa_sede, "sede": p.get("sede"),
			"facultad": p.get("facultad"), "estado": a.estado, "avance": avance,
			"logrados": c["logrados"], "en_proceso": c["en_proceso"], "no_logrados": c["no_logrados"],
			"pendientes": c["pendientes"], "evaluacion_externa": _("Sí") if avance >= umbral else _("No"),
			"fecha_cierre": a.fecha_cierre,
		})
	data.sort(key=lambda f: -f["avance"])
	return COLUMNAS, data, None, _grafico(data, umbral), _resumen(data, umbral)


COLUMNAS = [
	{"fieldname": "autoevaluacion", "label": _("Autoevaluación"), "fieldtype": "Link", "options": "Autoevaluacion", "width": 210},
	{"fieldname": "programa", "label": _("Programa"), "fieldtype": "Data", "width": 230},
	{"fieldname": "sede", "label": _("Sede"), "fieldtype": "Link", "options": "Unidad Organica", "width": 130},
	{"fieldname": "estado", "label": _("Estado"), "fieldtype": "Data", "width": 100},
	{"fieldname": "avance", "label": _("Avance (%)"), "fieldtype": "Percent", "width": 110},
	{"fieldname": "logrados", "label": _("Criterios logrados"), "fieldtype": "Int", "width": 90},
	{"fieldname": "en_proceso", "label": _("En proceso"), "fieldtype": "Int", "width": 90},
	{"fieldname": "no_logrados", "label": _("No logrados"), "fieldtype": "Int", "width": 90},
	{"fieldname": "pendientes", "label": _("Pendientes"), "fieldtype": "Int", "width": 90},
	{"fieldname": "evaluacion_externa", "label": _("Lista para evaluación externa"), "fieldtype": "Data", "width": 120},
	{"fieldname": "fecha_cierre", "label": _("Cierre previsto"), "fieldtype": "Date", "width": 110},
	{"fieldname": "facultad", "label": _("Facultad"), "fieldtype": "Link", "options": "Unidad Organica", "width": 160},
]


def _programas(nombres):
	"""{programa_sede: {nombre, sede, facultad}}."""
	if not nombres:
		return {}
	ps = frappe.get_all("Programa Sede", filters={"name": ["in", list(nombres)]}, fields=["name", "programa", "sede"], limit=0)
	progs = {p.name: p for p in frappe.get_all(
		"Programa", filters={"name": ["in", [x.programa for x in ps if x.programa]]},
		fields=["name", "nombre", "facultad"], limit=0)}
	return {x.name: {"nombre": (progs.get(x.programa) or {}).get("nombre"), "sede": x.sede,
					 "facultad": (progs.get(x.programa) or {}).get("facultad")} for x in ps}


def _juicios(autoevaluaciones):
	"""{autoevaluación: Counter(logrados, en_proceso, no_logrados, no_aplica, pendientes)} de sus criterios."""
	if not autoevaluaciones:
		return {}
	salida = {}
	for v in frappe.get_all("Valoracion Criterio", filters={"autoevaluacion": ["in", list(autoevaluaciones)]},
							fields=["autoevaluacion", "cumple"], limit=0):
		salida.setdefault(v.autoevaluacion, Counter())[ESTADO_CRITERIO.get(v.cumple or "", "pendientes")] += 1
	return salida


def _grafico(data, umbral):
	if not data:
		return None
	return {
		"data": {"labels": [f"{f['programa'][:22]} · {(f['sede'] or '').replace('SEDE-', '')[:10]}" for f in data],
				 "datasets": [{"name": _("Avance (%)"), "values": [f["avance"] for f in data]}],
				 "yMarkers": [{"label": _("Evaluación externa ({0} %)").format(int(umbral)), "value": umbral}]},
		"type": "bar", "colors": ["#2b6cb0"], "axisOptions": {"xIsSeries": 1}, "barOptions": {"spaceRatio": 0.4},
	}


def _resumen(data, umbral):
	en_marcha = [f for f in data if f["estado"] != "Planificada"]
	promedio = round(sum(f["avance"] for f in en_marcha) / len(en_marcha), 1) if en_marcha else 0
	listas = sum(1 for f in data if f["avance"] >= umbral)
	return [
		{"value": len(data), "label": _("Autoevaluaciones"), "datatype": "Int"},
		{"value": len(en_marcha), "label": _("Iniciadas"), "datatype": "Int", "indicator": "Blue"},
		{"value": promedio, "label": _("Avance promedio de las iniciadas (%)"), "datatype": "Float",
		 "indicator": "Green" if promedio >= umbral else "Orange" if promedio > 25 else "Red"},
		{"value": listas, "label": _("Listas para evaluación externa (≥ {0} %)").format(int(umbral)), "datatype": "Int",
		 "indicator": "Green" if listas else "Gray"},
	]
