# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Valoración de la atención de un reclamo por quien reclamó (ver `sgc/valoraciones.py`).

Solo la crea el formulario web con la clave de un solo uso que se envió al reclamante; nadie
tiene permiso de crearla ni de editarla en el Desk.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class ValoracionAtencion(Document):
	def validate(self):
		if not self.salida_no_conforme:
			frappe.throw(_("La valoración se hace desde el enlace que recibió por correo."))
		if self.is_new() and frappe.db.exists("Valoracion Atencion", {"salida_no_conforme": self.salida_no_conforme}):
			frappe.throw(_("Esta atención ya fue valorada."))
