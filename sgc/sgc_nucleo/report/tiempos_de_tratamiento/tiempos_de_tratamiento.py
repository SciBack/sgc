# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Tiempos de tratamiento: cuántos días pasa un registro en cada estado de su flujo.

Responde a dónde se atascan las cosas (ISO 9001 §9.1.3, §10.2): cuánto tarda una no
conformidad en analizarse, un documento en revisarse o una acción en verificarse. La idea
viene de Frappe CRM (`crm_status_change_log`), pero aquí no hace falta guardar nada nuevo:
todos estos DocTypes llevan `track_changes`, y Frappe anota cada cambio de `estado` en
`Version` con su hora. Por eso el informe también cubre lo que pasó antes de existir.

Para cada registro se reconstruyen sus tramos de estado (`tramos`): desde que se creó hasta
el primer cambio, y de cambio en cambio hasta hoy. El tramo de un estado final (cerrado,
publicado, obsoleto) no se cuenta: no es espera, es el final.

Los registros se leen con `get_list`, que aplica permisos y sede; el historial, solo el de
esos registros. Ojo: un cambio hecho con `db_set` no pasa por `Version` y no aparece.
"""

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from sgc.plazos import CIERRES as CIERRES_PLAZO

# Estados que cierran el registro: de ahí se mide «días hasta el cierre».
CIERRES = {
	**CIERRES_PLAZO,
	"Salida No Conforme": ("Cerrada",),
	"Evento Riesgo": ("Confirmado", "Descartado"),
	"Documento Controlado": ("Publicado",),
	"Ficha Caracterizacion Proceso": ("Publicado",),
}
# Estados finales además del cierre: su tramo tampoco es espera.
OTROS_FINALES = {"Documento Controlado": ("Obsoleto",), "Ficha Caracterizacion Proceso": ("Obsoleto",)}
POR_DEFECTO = "No Conformidad"


def tramos(creacion, estado_actual, cambios, ahora):
	"""Lista de `(estado, inicio, fin, en_curso)` de un registro.

	`cambios`: `[(fecha, estado_anterior, estado_nuevo)]` en orden. El primer tramo empieza al
	crearse, con el estado del que salió el primer cambio (o el actual, si nunca cambió).
	"""
	estado = cambios[0][1] if cambios else estado_actual
	inicio = get_datetime(creacion)
	salida = []
	for fecha, _anterior, nuevo in cambios:
		fecha = get_datetime(fecha)
		salida.append((estado, inicio, fecha, False))
		estado, inicio = nuevo, fecha
	salida.append((estado, inicio, get_datetime(ahora), True))
	return salida


def dias(inicio, fin):
	return max((fin - inicio).total_seconds(), 0) / 86400


def execute(filters=None):
	filters = frappe._dict(filters or {})
	tipo = filters.get("tipo") or POR_DEFECTO
	if tipo not in CIERRES:
		frappe.throw(_("No se miden tiempos de {0}.").format(_(tipo)))
	if not frappe.has_permission(tipo, "read"):
		frappe.throw(_("No tiene acceso a {0}.").format(_(tipo)), frappe.PermissionError)

	condiciones = {}
	if filters.get("desde") or filters.get("hasta"):
		condiciones["creation"] = ["between", [filters.get("desde") or "1900-01-01", filters.get("hasta") or "2999-12-31"]]
	registros = frappe.get_list(tipo, filters=condiciones, fields=["name", "creation", "estado"], limit=0)
	cambios = _cambios_de_estado(tipo, [r.name for r in registros])

	cierres = set(CIERRES[tipo])
	finales = cierres | set(OTROS_FINALES.get(tipo, ()))
	ahora = now_datetime()
	por_estado, hasta_cierre = {}, []
	for r in registros:
		propios = cambios.get(r.name, [])
		for estado, inicio, fin, en_curso in tramos(r.creation, r.estado, propios, ahora):
			if estado in finales:
				continue
			fila = por_estado.setdefault(estado, {"pasaron": [], "en_curso": []})
			(fila["en_curso"] if en_curso else fila["pasaron"]).append(dias(inicio, fin))
		primer_cierre = next((get_datetime(f) for f, _a, nuevo in propios if nuevo in cierres), None)
		if primer_cierre:
			hasta_cierre.append(dias(get_datetime(r.creation), primer_cierre))

	orden = [e for e in (frappe.get_meta(tipo).get_field("estado").options or "").split("\n") if e]
	data = []
	for estado in orden:
		if estado not in por_estado:
			continue
		f = por_estado[estado]
		data.append({
			"estado": _(estado),
			"pasaron": len(f["pasaron"]),
			"dias_promedio": _media(f["pasaron"]),
			"dias_max": round(max(f["pasaron"]), 1) if f["pasaron"] else None,
			"en_curso": len(f["en_curso"]),
			"dias_en_curso": _media(f["en_curso"]),
		})

	return _columnas(), data, None, _grafico(data), _resumen(registros, hasta_cierre)


def _cambios_de_estado(tipo, nombres):
	"""{registro: [(fecha, anterior, nuevo)]} leído de `Version`, en orden."""
	if not nombres:
		return {}
	versiones = frappe.get_all(
		"Version",
		filters={"ref_doctype": tipo, "docname": ["in", nombres], "data": ["like", '%"estado"%']},
		fields=["docname", "data", "creation"],
		order_by="creation asc",
	)
	salida = {}
	for v in versiones:
		datos = frappe.parse_json(v.data) or {}
		for campo, anterior, nuevo in datos.get("changed") or []:
			if campo == "estado" and anterior != nuevo:
				salida.setdefault(v.docname, []).append((v.creation, anterior, nuevo))
	return salida


def _media(valores):
	return round(sum(valores) / len(valores), 1) if valores else None


def _columnas():
	return [
		{"fieldname": "estado", "label": _("Estado"), "fieldtype": "Data", "width": 180},
		{"fieldname": "pasaron", "label": _("Pasaron por él"), "fieldtype": "Int", "width": 120},
		{"fieldname": "dias_promedio", "label": _("Días promedio"), "fieldtype": "Float", "precision": 1, "width": 120},
		{"fieldname": "dias_max", "label": _("Días máximo"), "fieldtype": "Float", "precision": 1, "width": 110},
		{"fieldname": "en_curso", "label": _("Están ahora"), "fieldtype": "Int", "width": 110},
		{"fieldname": "dias_en_curso", "label": _("Días que llevan"), "fieldtype": "Float", "precision": 1, "width": 130},
	]


def _grafico(data):
	if not data:
		return None
	return {
		"data": {
			"labels": [f["estado"] for f in data],
			"datasets": [{"name": _("Días promedio"), "values": [f["dias_promedio"] or 0 for f in data]}],
		},
		"type": "bar",
	}


def _resumen(registros, hasta_cierre):
	return [
		{"label": _("Registros"), "value": len(registros), "datatype": "Int"},
		{"label": _("Cerrados"), "value": len(hasta_cierre), "datatype": "Int"},
		{"label": _("Días promedio hasta el cierre"), "value": _media(hasta_cierre) or 0, "datatype": "Float",
		 "indicator": "Blue"},
	]
