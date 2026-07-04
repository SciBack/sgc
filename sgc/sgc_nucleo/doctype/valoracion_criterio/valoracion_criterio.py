# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ValoracionCriterio(Document):
	def on_update(self):
		"""Al valorar un criterio, recomputar el nivel propuesto de su estándar.

		El estándar padre del criterio es el `parent_elemento_marco` del criterio
		(criterio depth 3 -> estándar depth 2). El motor solo escribe `nivel_propuesto`
		en la Valoracion Estandar; el `nivel` oficial lo confirma el humano.

		Llamada directa (no enqueue): en F2 el recomputo de un estándar es liviano.
		"""
		if not self.autoevaluacion or not self.criterio:
			return

		estandar = frappe.db.get_value(
			"Elemento Marco", self.criterio, "parent_elemento_marco"
		)
		if not estandar:
			return

		# Import diferido para evitar ciclos en el arranque de Frappe.
		from sgc.scoring import proponer_nivel_estandar

		proponer_nivel_estandar(self.autoevaluacion, estandar)
