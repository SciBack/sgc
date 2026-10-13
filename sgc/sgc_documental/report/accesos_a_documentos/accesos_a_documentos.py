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

from sgc.documentos import DOCTYPE

FICHERO = "Fichero (enlace directo)"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return _columnas(), _filas(filters)


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
