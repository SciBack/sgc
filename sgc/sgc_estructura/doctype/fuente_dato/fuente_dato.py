# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Fuente de dato — criterio 8.1 del Estándar 8 (Coneau, programas).

De dónde sale cada dato, con quién responde por él y cada cuánto se recoge.

Hasta ahora esto vivía como texto libre en `Ficha Indicador.fuente_dato` y
`fuente_autoritativa`. Servía para leerlo, no para demostrar nada: no se podía
listar qué indicadores dependen de una fuente caída, ni quién responde por ella,
ni saber si dos fichas se referían a la misma fuente escrita de dos maneras.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class FuenteDato(Document):
	def validate(self):
		# Una fuente automática sin protocolo no se puede reproducir: quien venga
		# después no sabe por dónde entra el dato.
		if self.metodo_recojo in ("Automático", "Mixto") and not (self.protocolo or "").strip():
			frappe.throw(_("Una fuente {0} necesita indicar su protocolo.").format(self.metodo_recojo.lower()))

		# La fuente autoritativa es la que manda cuando el mismo dato está en
		# varios sitios. Si está de baja, ya no puede mandar.
		if self.es_autoritativa and self.estado == "Baja":
			frappe.throw(_("Una fuente dada de baja no puede seguir marcada como autoritativa."))
