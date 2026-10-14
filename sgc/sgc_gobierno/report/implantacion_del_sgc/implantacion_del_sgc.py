# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Implantación del SGC: ¿se está USANDO el sistema, o solo está instalado?

Mide en vivo los criterios de aceptación de una puesta en marcha (los del MVP del requerimiento
de UPeU, §11.3, que son los razonables para cualquier institución): diagnóstico CBC con su PDF,
documentos que pasaron el flujo completo, una autoevaluación cerrada, evidencias clasificadas,
indicadores con medición, acciones de mejora en seguimiento, revisión de seguridad y personas
usando el sistema.

Cada instancia ajusta las metas en `site_config.json`, clave `sgc_metas_implantacion`, por
ejemplo `{"documentos": 50, "evidencias": 500, "autoevaluacion_programa": "ENF-LIMA"}`. La
revisión de seguridad no se mide desde dentro: se declara en
`sgc_metas_implantacion.revision_seguridad` (`{"fecha": "2026-11-02", "resultado": "..."}`).

Son recuentos, no listados: no expone qué dice cada registro, solo cuántos hay.
"""

import time

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime

METAS = {
	"informes_cbc": 1,
	"documentos": 50,
	"autoevaluaciones": 1,
	"autoevaluacion_programa": None,
	"evidencias": 500,
	"indicadores_marco_pct": 100,
	"macroprocesos_pct": 100,
	"acciones_mejora": 30,
	"usuarios_activos": 15,
	"dias_actividad": 30,
	"revision_seguridad": None,
}


def metas():
	return {**METAS, **(frappe.conf.get("sgc_metas_implantacion") or {})}


def execute(filters=None):
	m = metas()
	data = [fila(*criterio(m)) for criterio in CRITERIOS]
	cumplidos = sum(1 for d in data if d["estado"] == ESTADOS[0])
	resumen = [
		{"value": f"{cumplidos} / {len(data)}", "label": _("Criterios cumplidos"),
		 "indicator": "Green" if cumplidos == len(data) else "Orange" if cumplidos else "Red", "datatype": "Data"},
	]
	return COLUMNAS, data, None, _grafico(data), resumen


ESTADOS = ("Cumple", "En curso", "Sin empezar")

COLUMNAS = [
	{"fieldname": "criterio", "label": _("Criterio"), "fieldtype": "Data", "width": 300},
	{"fieldname": "meta", "label": _("Meta"), "fieldtype": "Int", "width": 80},
	{"fieldname": "actual", "label": _("Actual"), "fieldtype": "Int", "width": 80},
	{"fieldname": "avance", "label": _("Avance"), "fieldtype": "Percent", "width": 90},
	{"fieldname": "estado", "label": _("Estado"), "fieldtype": "Data", "width": 110},
	{"fieldname": "falta", "label": _("Qué falta y dónde"), "fieldtype": "Data", "width": 520},
]


def fila(criterio, meta, actual, falta):
	meta = max(int(meta or 0), 1)
	actual = int(actual or 0)
	estado = ESTADOS[0] if actual >= meta else ESTADOS[1] if actual else ESTADOS[2]
	return {"criterio": criterio, "meta": meta, "actual": actual,
			"avance": round(min(100, 100 * actual / meta), 1), "estado": estado,
			"falta": "" if estado == ESTADOS[0] else falta}


def _grafico(data):
	return {
		"data": {"labels": [d["criterio"][:28] for d in data],
				 "datasets": [{"name": _("Avance"), "values": [d["avance"] for d in data]}]},
		"type": "bar", "colors": ["#2f6f4f"], "axisOptions": {"xIsSeries": 1},
	}


# ---------------------------------------------------------------------------- criterios

def _cbc(m):
	mejor, total_mejor, con_pdf = 0, 0, False
	for inf in frappe.get_all("Informe Cumplimiento", fields=["name", "pdf", "n_cumple", "n_parcial", "n_no_cumple"]):
		total = frappe.db.count("Cumplimiento CBC", {"parent": inf.name, "parenttype": "Informe Cumplimiento"})
		valoradas = (inf.n_cumple or 0) + (inf.n_parcial or 0) + (inf.n_no_cumple or 0)
		completo = total and valoradas == total
		if completo and inf.pdf:
			return _("Diagnóstico de condiciones básicas (CBC) con PDF"), m["informes_cbc"], 1, ""
		if valoradas >= mejor:
			mejor, total_mejor, con_pdf = valoradas, total, bool(inf.pdf)
	if not total_mejor:
		falta = _("No hay ningún informe de cumplimiento. Acreditación y licenciamiento → Informe de cumplimiento (SUNEDU) → Nuevo.")
	elif mejor < total_mejor:
		falta = _("El informe más avanzado tiene {0} de {1} condiciones valoradas.").format(mejor, total_mejor)
	else:
		falta = _("Están todas valoradas; falta generar el PDF del informe.") if not con_pdf else ""
	return _("Diagnóstico de condiciones básicas (CBC) con PDF"), m["informes_cbc"], 0, falta


def _documentos(m):
	publicados = frappe.db.count("Documento Controlado", {
		"estado": "Publicado", "elaborado_por": ["is", "set"], "revisado_por": ["is", "set"], "aprobado_por": ["is", "set"]})
	borrador = frappe.db.count("Documento Controlado", {"estado": "Borrador"})
	revision = frappe.db.count("Documento Controlado", {"estado": ["in", ["En revision", "Aprobado", "Observado"]]})
	falta = _("{0} en borrador y {1} a medio camino de su aprobación. Documentos → Documentos controlados.").format(borrador, revision)
	return _("Documentos con flujo completo (elaborado, revisado, aprobado y publicado)"), m["documentos"], publicados, falta


def _autoevaluacion(m):
	filtros = {"programa_sede": m["autoevaluacion_programa"]} if m["autoevaluacion_programa"] else {}
	cerradas = frappe.db.count("Autoevaluacion", {**filtros, "estado": "Cerrada"})
	abiertas = frappe.get_all("Autoevaluacion", filters={**filtros, "estado": ["!=", "Cerrada"]}, pluck="estado")
	donde = _(" de {0}").format(m["autoevaluacion_programa"]) if filtros else ""
	if abiertas:
		falta = _("Hay {0} en curso{1} (estados: {2}).").format(len(abiertas), donde, ", ".join(sorted(set(abiertas))))
	else:
		falta = _("No se ha iniciado ninguna{0}. Acreditación y licenciamiento → Autoevaluaciones → Nuevo.").format(donde)
	return _("Autoevaluación completa con el modelo de acreditación") + donde, m["autoevaluaciones"], cerradas, falta


def _evidencias(m):
	clasificadas = len(set(frappe.get_all("Trazabilidad", filters={"evidencia": ["is", "set"]}, pluck="evidencia")))
	total = frappe.db.count("Evidencia")
	inicio = time.perf_counter()
	frappe.get_all("Evidencia", fields=["name", "titulo", "estado"], order_by="modified desc", limit=500)
	ms = round(1000 * (time.perf_counter() - inicio))
	falta = _("{0} evidencias, {1} vinculadas a un criterio o proceso. Listar 500 tarda {2} ms. "
			  "Para cargarlas en bloque: Acreditación y licenciamiento → Carga masiva de evidencias.").format(total, clasificadas, ms)
	return _("Evidencias clasificadas y recuperables"), m["evidencias"], clasificadas, falta


def _indicadores_marco(m):
	del_marco = frappe.get_all("Indicador", filters={"marco_normativo": ["is", "set"]}, pluck="name")
	medidos = set(frappe.get_all("Valor Indicador", filters={"indicador": ["in", del_marco or [""]]}, pluck="indicador"))
	meta = round(len(del_marco) * m["indicadores_marco_pct"] / 100)
	falta = _("{0} de {1} indicadores de los marcos de acreditación tienen alguna medición. Indicadores → Fichas de indicador.").format(len(medidos), len(del_marco))
	return _("Indicadores de acreditación calculados"), meta, len(medidos), falta


def _macroprocesos(m):
	macros = frappe.get_all("Proceso", filters={"nivel_bpm": "Macroproceso"}, fields=["name", "lft", "rgt"])
	if not macros:
		macros = frappe.get_all("Proceso", filters={"parent_proceso": ["is", "not set"]}, fields=["name", "lft", "rgt"])
	medidos = set(frappe.get_all("Valor Indicador", pluck="indicador"))
	con_medicion = 0
	for p in macros:
		procesos = frappe.get_all("Proceso", filters={"lft": [">=", p.lft], "rgt": ["<=", p.rgt]}, pluck="name")
		indicadores = frappe.get_all("Indicador", filters={"proceso": ["in", procesos]}, pluck="name")
		con_medicion += any(i in medidos for i in indicadores)
	meta = round(len(macros) * m["macroprocesos_pct"] / 100)
	falta = _("{0} de {1} macroprocesos tienen algún indicador de proceso medido.").format(con_medicion, len(macros))
	return _("Macroprocesos con indicadores de proceso medidos"), meta, con_medicion, falta


def _acciones(m):
	seguidas = frappe.db.count("Accion Mejora", {"responsable": ["is", "set"], "fecha_compromiso": ["is", "set"]})
	aviso = frappe.db.get_value("Notification", {"document_type": "Accion Mejora", "event": "Days Before"}, "enabled")
	falta = _("{0} acciones con responsable y fecha de compromiso. Mejora continua → Planes de mejora.").format(seguidas)
	if not aviso:
		falta += " " + _("El aviso de acción por vencer está apagado.")
	return _("Acciones de mejora en seguimiento con alertas"), m["acciones_mejora"], seguidas, falta


def _seguridad(m):
	revision = m.get("revision_seguridad") or {}
	if revision.get("fecha"):
		return _("Pruebas de seguridad básica (OWASP Top 10)"), 1, 1, ""
	return (_("Pruebas de seguridad básica (OWASP Top 10)"), 1, 0,
			_("Sin revisión registrada. Se declara en site_config: sgc_metas_implantacion.revision_seguridad."))


def _usuarios(m):
	from sgc.estandar import roles

	desde = str(add_days(now_datetime(), -int(m["dias_actividad"])))
	con_rol = set(frappe.get_all("Has Role", filters={"role": ["in", list(roles())], "parenttype": "User"}, pluck="parent"))
	activos = frappe.get_all("User", filters={"name": ["in", list(con_rol) or [""]], "enabled": 1,
											  "user_type": "System User", "last_login": [">", desde]}, pluck="name")
	activos = [u for u in activos if u not in ("Administrator", "Guest")]
	falta = _("{0} de {1} personas con un rol del SGC entraron en los últimos {2} días. "
			  "La capacitación se registra fuera del sistema.").format(len(activos), len(con_rol), m["dias_actividad"])
	return _("Personas operando el sistema"), m["usuarios_activos"], len(activos), falta


CRITERIOS = [_cbc, _documentos, _autoevaluacion, _evidencias, _indicadores_marco, _macroprocesos,
			 _acciones, _seguridad, _usuarios]
