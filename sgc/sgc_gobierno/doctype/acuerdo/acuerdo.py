# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import getdate, nowdate


class Acuerdo(Document):
	def validate(self):
		self._marcar_vencido_si_expiro()

	def _marcar_vencido_si_expiro(self):
		"""fecha_compromiso pasada y sin cerrar -> Vencido.

		Solo actúa sobre los estados NO terminales (Pendiente/En proceso); un
		Acuerdo ya Cumplido/Cancelado/Vencido no se toca. Acuerdo no tiene
		Workflow nativo (a diferencia de Evidencia) -- la asignación directa
		aquí es segura; si en el futuro se le agrega un Workflow activo, este
		flip deberá moverse a `frappe.db.set_value` fuera de `validate()`
		(mismo motivo documentado en `Evidencia._marcar_vencida_si_expiro`).
		"""
		if self.fecha_compromiso and getdate(self.fecha_compromiso) < getdate(nowdate()):
			if self.estado in ("Pendiente", "En proceso"):
				self.estado = "Vencido"
