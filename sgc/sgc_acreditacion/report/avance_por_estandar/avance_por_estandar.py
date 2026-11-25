# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Avance por estándar: el tablero de UNA autoevaluación, para quien la lleva y para la dirección de calidad.

Una fila por estándar del modelo con su % de avance y un semáforo (logrado / en proceso / no logrado, con los
umbrales de `scoring.umbrales`), cuántos de sus criterios están logrados, en proceso, no logrados o
pendientes, y el nivel que propone el sistema (NL/L/LP) y el confirmado. El resumen dice cuánto lleva la
autoevaluación y cuánto le falta para el umbral de la evaluación externa.
"""

from collections import Counter

import frappe
from frappe import _

from sgc import scoring

JUICIO = {"Cumple": "logrados", "Cumple parcial": "en_proceso", "No cumple": "no_logrados", "No aplica": "no_aplica"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.autoevaluacion:
		return COLUMNAS, [], _("Elija una autoevaluación."), None, []
	ae = frappe.get_doc("Autoevaluacion", filters.autoevaluacion)
	ae.check_permission("read")

	estandares = frappe.get_all(
		"Elemento Marco", filters={"marco_normativo": ae.marco_normativo, "tipo": "Estandar"},
		fields=["name", "codigo", "denominacion"], order_by="lft asc", limit=0)
	juicios = {v.criterio: v.cumple for v in frappe.get_all(
		"Valoracion Criterio", filters={"autoevaluacion": ae.name}, fields=["criterio", "cumple"], limit=0)}
	niveles = {v.elemento_marco: v for v in frappe.get_all(
		"Valoracion Estandar", filters={"autoevaluacion": ae.name},
		fields=["elemento_marco", "nivel_propuesto", "nivel", "confirmado"], limit=0)}

	data = []
	for est in estandares:
		criterios = scoring._criterios_de_estandar(est.name, autoevaluacion=ae.name)
		c = Counter(JUICIO.get(juicios.get(cr) or "", "pendientes") for cr in criterios)
		avance = scoring.avance_por_evidencias(ae.name, estandar=est.name)
		if avance is None:  # sin evidencias esperadas: los criterios con juicio
			con_juicio = c["logrados"] + c["en_proceso"] + c["no_logrados"]
			avance = round(100 * c["logrados"] / con_juicio, 2) if con_juicio else 0.0
		nivel = niveles.get(est.name) or {}
		data.append({
			"estandar": est.name, "denominacion": f"{(est.codigo or '').rsplit('-', 1)[-1]}. {est.denominacion}",
			"avance": avance, "semaforo": scoring.valoracion_por_avance(avance), "criterios": len(criterios),
			"logrados": c["logrados"], "en_proceso": c["en_proceso"], "no_logrados": c["no_logrados"],
			"pendientes": c["pendientes"], "nivel_propuesto": nivel.get("nivel_propuesto"),
			"nivel": nivel.get("nivel") if nivel.get("confirmado") else None,
		})
	total = scoring._calcular_avance_pct(ae.name) if ae.estado != "Planificada" else 0.0
	return COLUMNAS, data, None, _grafico(data), _resumen(data, total)


COLUMNAS = [
	{"fieldname": "denominacion", "label": _("Estándar"), "fieldtype": "Data", "width": 320},
	{"fieldname": "avance", "label": _("Avance (%)"), "fieldtype": "Percent", "width": 110},
	{"fieldname": "semaforo", "label": _("Estado"), "fieldtype": "Data", "width": 110},
	{"fieldname": "criterios", "label": _("Criterios"), "fieldtype": "Int", "width": 80},
	{"fieldname": "logrados", "label": _("Logrados"), "fieldtype": "Int", "width": 85},
	{"fieldname": "en_proceso", "label": _("En proceso"), "fieldtype": "Int", "width": 90},
	{"fieldname": "no_logrados", "label": _("No logrados"), "fieldtype": "Int", "width": 90},
	{"fieldname": "pendientes", "label": _("Pendientes"), "fieldtype": "Int", "width": 90},
	{"fieldname": "nivel_propuesto", "label": _("Nivel propuesto"), "fieldtype": "Data", "width": 100},
	{"fieldname": "nivel", "label": _("Nivel confirmado"), "fieldtype": "Data", "width": 100},
	{"fieldname": "estandar", "label": _("Elemento"), "fieldtype": "Link", "options": "Elemento Marco", "width": 110},
]


def _grafico(data):
	if not data:
		return None
	return {
		"data": {"labels": [f["denominacion"].split(".")[0] for f in data],
				 "datasets": [{"name": _("Avance (%)"), "values": [f["avance"] for f in data]}]},
		"type": "bar", "colors": ["#2b6cb0"], "axisOptions": {"xIsSeries": 1},
	}


def _resumen(data, total):
	u = scoring.umbrales()
	color = {"Logrado": "Green", "En proceso": "Orange", "No logrado": "Red"}[scoring.valoracion_por_avance(total)]
	falta = max(0.0, round(u["evaluacion_externa"] - total, 1))
	suma = lambda clave: sum(f[clave] for f in data)  # noqa: E731
	return [
		{"value": total, "label": _("Avance de la autoevaluación (%)"), "datatype": "Float", "indicator": color},
		{"value": falta, "label": _("Le faltan para la evaluación externa (puntos)"), "datatype": "Float",
		 "indicator": "Green" if not falta else "Orange"},
		{"value": suma("logrados"), "label": _("Criterios logrados"), "datatype": "Int", "indicator": "Green"},
		{"value": suma("en_proceso"), "label": _("En proceso"), "datatype": "Int", "indicator": "Orange"},
		{"value": suma("no_logrados"), "label": _("No logrados"), "datatype": "Int", "indicator": "Red"},
		{"value": suma("pendientes"), "label": _("Pendientes"), "datatype": "Int", "indicator": "Gray"},
	]
