# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Trazabilidad — vínculo N:M entre una Evidencia y un elemento del marco y/o un
proceso (M09).

Es el mecanismo canónico que el Informe de Autoevaluación (sgc.informe) consume
para listar qué evidencias respaldan cada estándar/criterio. Una evidencia puede
tener varias Trazabilidad (a criterio, a CBC, a proceso — RNF09); un elemento se
sustenta en varias evidencias.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class Trazabilidad(Document):
	def validate(self):
		# Un vínculo que no apunta a nada no traza nada.
		if not self.elemento_marco and not self.proceso:
			frappe.throw(
				_("La Trazabilidad debe vincular la evidencia a un elemento del "
				  "marco, a un proceso, o a ambos."),
				title=_("Vínculo vacío"),
			)

		# Evitar duplicar el mismo vínculo (misma evidencia al mismo destino).
		# Un Link vacío se guarda como NULL en Postgres, y NULL no matchea "" en un
		# filtro de igualdad → hay que buscarlo con "is not set", no con or "".
		filtros = {"evidencia": self.evidencia, "name": ["!=", self.name or ""]}
		filtros["elemento_marco"] = self.elemento_marco if self.elemento_marco else ["is", "not set"]
		filtros["proceso"] = self.proceso if self.proceso else ["is", "not set"]
		if frappe.db.exists("Trazabilidad", filtros):
			frappe.throw(
				_("Ya existe una Trazabilidad de esta evidencia hacia el mismo destino."),
				title=_("Vínculo duplicado"),
			)
