# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Lista Maestra de Documentos Controlados — export a Excel (RF-B03/T06).

La "Lista Maestra" es el inventario de TODOS los `Documento Controlado` con su
estado de control documental (versión vigente, estado del ciclo de vida, fecha
de próxima revisión, dueño del proceso). La norma (ISO 21001 cl. 7.5, replicada
en el procedimiento DTN-Pro-01 de SUNEDU) exige mantener ese inventario
disponible; aquí se materializa como un .xlsx descargable.

El .xlsx se arma con el helper nativo de Frappe `make_xlsx`, que recibe una
lista de filas (`[encabezados, ...datos]`) y devuelve un BytesIO; la descarga
sigue el patrón estándar de Frappe (`frappe.response["type"] = "binary"`).
"""

import frappe
from frappe import _
from frappe.utils import formatdate
from frappe.utils.xlsxutils import make_xlsx

# Encabezados de negocio de la Lista Maestra (orden = orden de columnas del xlsx).
_CABECERAS = [
	"Código",
	"Título",
	"Tipo de documento",
	"Proceso",
	"Versión",
	"Estado",
	"Próxima revisión",
	"Dueño de proceso",
]


def _mapa_procesos():
	"""Cache {codigo_proceso: (denominación, nombre_del_dueño)} en una sola consulta.

	`Documento Controlado.proceso` es un Link a `Proceso` (su `name` == código).
	La denominación legible y el dueño de proceso viven en el `Proceso`, no en el
	documento, así que se resuelven aquí para no disparar N consultas por fila.
	El dueño se muestra por su nombre completo cuando el User lo tiene.
	"""
	mapa = {}
	for p in frappe.get_all(
		"Proceso",
		fields=["name", "proceso", "responsable"],
		ignore_permissions=True,
	):
		dueno = ""
		if p.get("responsable"):
			dueno = (
				frappe.db.get_value("User", p["responsable"], "full_name")
				or p["responsable"]
			)
		mapa[p["name"]] = (p.get("proceso") or p["name"], dueno)
	return mapa


def _filas_lista_maestra(estado=None, proceso=None):
	"""Filas de datos (sin encabezado) ordenadas por proceso y luego código."""
	filtros = {}
	if estado:
		filtros["estado"] = estado
	if proceso:
		filtros["proceso"] = proceso

	documentos = frappe.get_all(
		"Documento Controlado",
		filters=filtros,
		fields=[
			"name",
			"titulo",
			"tipo_documento",
			"proceso",
			"version",
			"estado",
			"fecha_proxima_revision",
		],
		# Orden primario por proceso, secundario por código (== name).
		order_by="proceso asc, name asc",
	)

	procesos = _mapa_procesos()
	filas = []
	for d in documentos:
		denominacion, dueno = procesos.get(d.get("proceso"), (d.get("proceso") or "", ""))
		filas.append([
			d.get("name") or "",
			d.get("titulo") or "",
			d.get("tipo_documento") or "",
			denominacion,
			d.get("version") or "",
			d.get("estado") or "",
			formatdate(d["fecha_proxima_revision"]) if d.get("fecha_proxima_revision") else "",
			dueno,
		])
	return filas


@frappe.whitelist()
def exportar_lista_maestra(estado=None, proceso=None):
	"""Genera y descarga la Lista Maestra de Documentos Controlados en .xlsx.

	Filtros opcionales:
	  - `estado`:  limita a un estado del ciclo de vida (Borrador, Publicado, ...).
	  - `proceso`: limita a un `Proceso` concreto (su código/name).

	Devuelve el archivo al cliente vía `frappe.response` (patrón estándar de
	Frappe para descargas binarias desde un método whitelisted): no retorna un
	valor útil, sino que setea filename/filecontent/type en la respuesta.
	"""
	filas = _filas_lista_maestra(estado=estado, proceso=proceso)

	# make_xlsx recibe [encabezados, ...datos] y devuelve un BytesIO listo.
	datos = [_CABECERAS] + filas
	xlsx_file = make_xlsx(datos, "Lista Maestra")

	frappe.response["filename"] = "Lista-Maestra-Documentos.xlsx"
	frappe.response["filecontent"] = xlsx_file.getvalue()
	frappe.response["type"] = "binary"
