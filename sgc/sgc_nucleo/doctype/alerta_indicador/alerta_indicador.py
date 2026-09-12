# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Alerta sobre un indicador — criterio 8.1 del Estándar 8 (Coneau, programas).

El estándar pide «procedimientos de aplicación periódica para el recojo y
análisis de los resultados». Una alerta es el rastro de ese análisis cuando algo
no cuadra: la meta no se alcanzó, el período cerró sin medición o una regla de
validación falló.

Se guarda como documento y no como notificación efímera a propósito. Ante un
evaluador, «saltó un aviso» no vale; lo que vale es que conste qué se detectó,
quién era el responsable, cuándo se cerró y —si se descartó— por qué.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from sgc.naming import codigo_anual


class AlertaIndicador(Document):
	def before_insert(self):
		if not self.codigo:
			self.codigo = codigo_anual(self.doctype, "ALE")
		if not self.fecha_deteccion:
			self.fecha_deteccion = now_datetime()
		# Si nadie la asignó, responde quien responde por el indicador. Una alerta
		# sin dueño no la atiende nadie.
		if not self.responsable:
			self.responsable = frappe.db.get_value(
				"Ficha Indicador", {"indicador": self.indicador}, "responsable"
			)

	def validate(self):
		cerrada = self.estado in ("Resuelta", "Descartada")

		if cerrada and not self.fecha_cierre:
			self.fecha_cierre = now_datetime()
		if not cerrada and self.fecha_cierre:
			self.fecha_cierre = None

		# Descartar es una decisión, no un barrido: tiene que quedar por escrito.
		if self.estado == "Descartada" and not (self.justificacion_descarte or "").strip():
			frappe.throw(_("Para descartar una alerta hay que justificarlo."))
