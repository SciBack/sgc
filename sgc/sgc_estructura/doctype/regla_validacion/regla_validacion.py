# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Regla de validación de datos — criterio 8.1 del Estándar 8 (Coneau, programas).

El criterio exige mecanismos que garanticen la **integridad** de los datos. Este
DocType declara qué se considera un dato íntegro, de forma que la regla sea
consultable y auditable en lugar de vivir escondida en el código.

Aquí se declara la regla; aplicarla es trabajo de quien carga el valor.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class ReglaValidacion(Document):
	def validate(self):
		# Una regla que no se ata ni a una fuente ni a un indicador no se puede
		# disparar nunca: no aplicaría a nada.
		if not self.fuente_dato and not self.indicador:
			frappe.throw(_("Indica al menos la fuente de dato o el indicador al que aplica la regla."))

		if self.tipo_regla in ("Rango", "Variación entre períodos"):
			if self.valor_min is None and self.valor_max is None:
				frappe.throw(_("Una regla de {0} necesita un mínimo, un máximo o ambos.").format(self.tipo_regla))
			if self.valor_min is not None and self.valor_max is not None and self.valor_min > self.valor_max:
				frappe.throw(_("El mínimo no puede ser mayor que el máximo."))

		if self.tipo_regla == "Coherencia entre campos" and not (self.expresion or "").strip():
			frappe.throw(_("Una regla de coherencia necesita su expresión."))
