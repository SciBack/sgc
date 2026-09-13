# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Tablero de indicadores — criterio 8.6 del Estándar 8 (Coneau, programas).

El criterio pide que la información esté «accesible para el personal directivo y
docente encargado de tomar decisiones sobre la gestión de mejoras». Por eso el
tablero se define **por rol** y no por persona: lo que se acredita es que el
cargo tiene acceso, no que un usuario concreto lo tuviera.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class TableroIndicadores(Document):
	def validate(self):
		# El ámbito y su objeto van juntos: un tablero «de programa» sin programa
		# no filtra nada y acaba enseñando datos de toda la institución.
		if self.ambito == "Unidad orgánica" and not self.unidad_organica:
			frappe.throw(_("Un tablero de ámbito «Unidad orgánica» necesita su unidad."))
		if self.ambito == "Programa-sede" and not self.programa_sede:
			frappe.throw(_("Un tablero de ámbito «Programa-sede» necesita su programa-sede."))
		if self.ambito == "Institucional":
			self.unidad_organica = None
			self.programa_sede = None

		if not self.indicadores:
			frappe.throw(_("Un tablero sin indicadores no muestra nada."))

		repetidos = self._repetidos()
		if repetidos:
			frappe.throw(_("Hay indicadores repetidos en el tablero: {0}").format(", ".join(repetidos)))

		for i, fila in enumerate(self.indicadores, start=1):
			if not fila.orden:
				fila.orden = i

	def _repetidos(self) -> list[str]:
		vistos, repes = set(), []
		for fila in self.indicadores:
			if fila.indicador in vistos:
				repes.append(fila.indicador)
			vistos.add(fila.indicador)
		return repes
