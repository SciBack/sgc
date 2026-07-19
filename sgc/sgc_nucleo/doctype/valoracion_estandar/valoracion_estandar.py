# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ValoracionEstandar(Document):
	def validate(self):
		"""Bloquea creación/edición si la Autoevaluación padre ya está Cerrada (submit).

		'Valoracion Estandar' es un DocType standalone (Link `autoevaluacion`, no
		child table) -- Frappe NO lo protege automáticamente cuando la Autoevaluacion
		pasa a docstatus=1 vía el workflow nativo (F4). Sin este guard, el snapshot
		del marco quedaría inmutable pero los datos de valoración (incluido el `nivel`
		oficial confirmado por humano) seguirían mutables, contradiciendo el propósito
		de la feature. Va primero en validate() para fallar rápido.

		Esto también bloquea `sgc.confirmacion.confirmar_nivel` tras el cierre --
		correcto: esa función escribe con `ignore_permissions=True` pero el doc pasa
		igual por `validate()`, y confirmar el nivel oficial de un estándar es
		precisamente la acción humana que debe ocurrir ANTES de "Cerrar" (workflow:
		Consolidada -> Cerrar -> Cerrada), nunca después. NO bloquea, en cambio,
		`sgc.confirmacion.finalizar_vigencia`: esa función solo LEE Valoracion
		Estandar y escribe `Autoevaluacion.resultado_vigencia` vía
		`frappe.db.set_value` directo (no pasa por `validate()` de ningún doc) --
		fuera del alcance de este guard; si necesita bloquearse tras el cierre
		también, es responsabilidad del guard en `autoevaluacion.py`/`scoring.py`.
		"""
		if self.autoevaluacion and frappe.db.get_value(
			"Autoevaluacion", self.autoevaluacion, "docstatus"
		) == 1:
			frappe.throw(
				_(
					"La autoevaluación ya fue cerrada y enviada; sus valoraciones "
					"quedan inmutables. Si necesita corregir un dato, cancele y "
					"reabra la autoevaluación (flujo nativo de Frappe: cancel + amend)."
				),
				title=_("Autoevaluación cerrada"),
			)
