# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Quién abrió o se llevó cada documento controlado, y cuándo (#36).

Une tres registros que viven en el mismo `Access Log` de Frappe:

- **Consulta** y **Descarga**: los deja `sgc.documentos` al abrir el visor de la
  ficha y al descargar desde ella, contra el documento.
- **Fichero (enlace directo)**: lo deja Frappe en cada descarga por la URL del
  fichero (`frappe/utils/response.py:305`), contra el `File`. Aquí se traduce al
  documento del que cuelga. Hasta #36 el visor cargaba el PDF por esa URL, así
  que en los registros anteriores esta fila mezcla aperturas y descargas.

## Permisos

`Access Log` solo lo lee System Manager, así que se consulta con `get_all`. El
informe se restringe por rol (DPGC, Analista, System Manager) en su JSON, y no
expone nada que esos roles no puedan ver ya en los documentos.
"""
import frappe
from frappe import _
from frappe.utils import add_days, getdate

from sgc.documentos import CONSULTA, DESCARGA, DOCTYPE

FICHERO = "Fichero (enlace directo)"
# Hasta este tramo el gráfico va por días (con los días sin accesos a cero); más largo, por meses.
DIAS_MAXIMOS_POR_DIA = 92
COLOR_ACCESO = {CONSULTA: "#5e64ff", DESCARGA: "#ffa00a", FICHERO: "#c0c6cc"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = _filas(filters)
	return _columnas(), data, None, _grafico(data), _resumen(data)


def _columnas():
	return [
		{"fieldname": "fecha", "label": _("Fecha"), "fieldtype": "Datetime", "width": 160},
		{"fieldname": "usuario", "label": _("Usuario"), "fieldtype": "Link", "options": "User", "width": 220},
		{"fieldname": "documento", "label": _("Documento"), "fieldtype": "Link", "options": DOCTYPE, "width": 200},
		{"fieldname": "titulo", "label": _("Título"), "fieldtype": "Data", "width": 260},
		{"fieldname": "acceso", "label": _("Acceso"), "fieldtype": "Data", "width": 160},
		{"fieldname": "formato", "label": _("Formato"), "fieldtype": "Data", "width": 80},
	]


def _filtros_comunes(filters):
	f = {}
	if filters.usuario:
		f["user"] = filters.usuario
	if filters.desde and filters.hasta:
		f["creation"] = ["between", [filters.desde, f"{filters.hasta} 23:59:59"]]
	elif filters.desde:
		f["creation"] = [">=", filters.desde]
	elif filters.hasta:
		f["creation"] = ["<=", f"{filters.hasta} 23:59:59"]
	return f


def _filas(filters):
	comunes = _filtros_comunes(filters)
	campos = ["creation", "user", "reference_document", "method", "file_type"]

	del_documento = dict(comunes, export_from=DOCTYPE)
	if filters.documento:
		del_documento["reference_document"] = filters.documento
	filas = [
		{
			"fecha": r.creation,
			"usuario": r.user,
			"documento": r.reference_document,
			"acceso": r.method,
			"formato": r.file_type,
		}
		for r in frappe.get_all("Access Log", filters=del_documento, fields=campos, limit=0)
	]

	ficheros = _ficheros_de_documentos(filters.documento)
	if ficheros:
		del_fichero = dict(comunes, export_from="File", reference_document=["in", list(ficheros)])
		filas += [
			{
				"fecha": r.creation,
				"usuario": r.user,
				"documento": ficheros[r.reference_document],
				"acceso": FICHERO,
				"formato": r.file_type,
			}
			for r in frappe.get_all("Access Log", filters=del_fichero, fields=campos, limit=0)
		]

	titulos = _titulos({f["documento"] for f in filas})
	for f in filas:
		f["titulo"] = titulos.get(f["documento"], "")
	return sorted(filas, key=lambda f: f["fecha"], reverse=True)


def _ficheros_de_documentos(documento=None):
	"""{nombre del File: documento del que cuelga}."""
	filtros = {"attached_to_doctype": DOCTYPE}
	if documento:
		filtros["attached_to_name"] = documento
	return {
		r.name: r.attached_to_name
		for r in frappe.get_all("File", filters=filtros, fields=["name", "attached_to_name"], limit=0)
	}


def _titulos(nombres):
	if not nombres:
		return {}
	return dict(
		frappe.get_all(
			DOCTYPE, filters={"name": ["in", list(nombres)]}, fields=["name", "titulo"], as_list=True, limit=0
		)
	)


def _grafico(data):
	"""Accesos en el tiempo, una línea por tipo de acceso, de las mismas filas que la tabla."""
	if not data:
		return None
	dias = sorted({getdate(f["fecha"]) for f in data})
	por_dia = (dias[-1] - dias[0]).days <= DIAS_MAXIMOS_POR_DIA
	# Los tramos sin accesos cuentan como 0: sin ellos la línea uniría puntos lejanos.
	if por_dia:
		etiquetas = [str(getdate(add_days(dias[0], n))) for n in range((dias[-1] - dias[0]).days + 1)]
	else:
		primero, ultimo = dias[0].year * 12 + dias[0].month - 1, dias[-1].year * 12 + dias[-1].month - 1
		etiquetas = [f"{m // 12:04d}-{m % 12 + 1:02d}" for m in range(primero, ultimo + 1)]

	def tramo(fila):
		fecha = str(getdate(fila["fecha"]))
		return fecha if por_dia else fecha[:7]

	accesos = [a for a in (CONSULTA, DESCARGA, FICHERO) if any(f["acceso"] == a for f in data)]
	accesos += sorted({f["acceso"] for f in data} - set(accesos) - {None})
	datasets = []
	for acceso in accesos:
		cuenta = dict.fromkeys(etiquetas, 0)
		for f in data:
			if f["acceso"] == acceso:
				cuenta[tramo(f)] += 1
		datasets.append({"name": _(acceso), "values": [cuenta[e] for e in etiquetas]})
	return {
		"data": {"labels": etiquetas, "datasets": datasets},
		"type": "line",
		"colors": [COLOR_ACCESO.get(a, "#7cd6fd") for a in accesos],
		"lineOptions": {"regionFill": 1},
	}


def _resumen(data):
	return [
		{"label": _("Accesos"), "value": len(data), "datatype": "Int"},
		{"label": _("Consultas"), "value": sum(1 for f in data if f["acceso"] == CONSULTA), "datatype": "Int"},
		{"label": _("Descargas"), "value": sum(1 for f in data if f["acceso"] == DESCARGA), "datatype": "Int"},
		{"label": _("Usuarios distintos"), "value": len({f["usuario"] for f in data}), "datatype": "Int"},
	]
