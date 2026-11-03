# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Calificación de una persona en una competencia (ver `sgc/competencias.py`).

Quién la otorga y quién la revoca lo sella el sistema, nunca el formulario, y nadie se
califica a sí mismo: la evaluación de la competencia la hace otra persona (ISO 19011 §7.4).
"""

import frappe
from frappe import _
from frappe.model.document import Document

from sgc import competencias


class CalificacionPersonal(Document):
	def validate(self):
		if self.is_new():
			if self.usuario == frappe.session.user:
				frappe.throw(_("Nadie registra su propia calificación: la otorga otra persona."),
							 title=_("Calificación propia"))
			self.otorgada_por = frappe.session.user
		self._sellar_revocacion()
		vigencia = frappe.db.get_value("Competencia", self.competencia, "vigencia_meses")
		self.vence = competencias.fecha_de_vencimiento(self.fecha_otorgamiento, vigencia)
		self.estado = competencias.calcular_estado(self.vence, self.revocada)

	def _sellar_revocacion(self):
		if not self.revocada:
			self.motivo_revocacion = None
			self.revocada_por = None
			return
		if not (self.motivo_revocacion or "").strip():
			frappe.throw(_("Indique el motivo de la revocación."), title=_("Revocación"))
		anterior = self.get_doc_before_save()
		if not anterior or not anterior.revocada:
			self.revocada_por = frappe.session.user
