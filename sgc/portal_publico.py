# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Contrato de lectura del portal público de procesos.

Existe por una razón concreta de **transporte**, no de comodidad.

`Ficha Caracterizacion Proceso.datos_ficha()` es un método de DOCUMENTO, y esos
solo se alcanzan por la API v2 (`/api/v2/document/<dt>/<name>/method/<m>`). Esa
ruta hace, en `frappe/api/v2.py`:

    frappe.response.docs.append(doc.as_dict())

es decir, **añade el documento entero al lado del resultado**, y `as_dict()` trae
`owner` y `modified_by` de la ficha y de todas sus tablas hijas. Medido en el lab
el 13-sep-2026 sobre `FICHA-S04.04`:

    respuesta v2 = {data, docs}
      data →  0 metadatos de persona   (la proyección de datos_ficha)
      docs → 46 metadatos de persona   (el documento completo, por cuenta del canal)

Por bien que proyecte el método, **el protocolo añade lo que nadie pidió**. Un
consumidor que serialice la respuesta entera publica los 46 sin enterarse, y no lo
ve revisando `data`, que está limpio.

Los métodos de MÓDULO no tienen ese problema: `/api/method/sgc.portal_publico.ficha`
devuelve `{message: ...}` y nada más — verificado, 0 metadatos. Así que el portal
llama aquí y nunca a la v2.

Esta es la sexta vez que el mismo patrón muerde a este portal: antes fueron el PDF
que imprimía las firmas, los campos `Attach` cuyo valor es la ruta al fichero
privado, los adjuntos que se sirven por permiso de doctype sin mirar el estado, las
tablas hijas volcadas con `as_dict()`, y un `Link` a `User` en un campo de negocio.
La regla que sale de todas: **en una vitrina pública no basta con declarar qué
campos salen; hay que mirar qué entrega cada canal.**
"""
import frappe
from frappe import _

DOCTYPE_FICHA = "Ficha Caracterizacion Proceso"
ESTADO_PUBLICO = "Publicado"


@frappe.whitelist()
def ficha(nombre: str) -> dict | None:
	"""Los datos publicables de una ficha, o nada si no está publicada.

	Mismo contrato que `sgc.ficha_pdf.pdf_publicado`: se pregunta por la ficha y se
	recibe el contenido o `None`. Comprueba el estado **además** del permiso, porque
	el permiso de Frappe no mira el estado del documento.
	"""
	if not frappe.has_permission(DOCTYPE_FICHA, ptype="read", doc=nombre):
		frappe.throw(_("Sin permiso sobre {0}").format(nombre), frappe.PermissionError)
	if frappe.db.get_value(DOCTYPE_FICHA, nombre, "estado") != ESTADO_PUBLICO:
		return None
	return frappe.get_doc(DOCTYPE_FICHA, nombre).datos_ficha()
