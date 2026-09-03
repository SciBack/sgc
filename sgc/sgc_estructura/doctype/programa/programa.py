# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Programa(Document):
	def validate(self):
		self._normalizar_codigos()
		self._validar_codigos_unicos()
		self._validar_codigo_principal()

	def _normalizar_codigos(self):
		"""Los códigos oficiales se comparan y publican en mayúsculas y sin espacios.

		El ente rector los emite así; permitir variantes haría que el mismo código
		conviva escrito de dos formas y que el cruce con otros sistemas falle.
		"""
		if self.codigo_oficial:
			self.codigo_oficial = self.codigo_oficial.strip().upper()
		for fila in self.codigos_oficiales or []:
			if fila.codigo:
				fila.codigo = fila.codigo.strip().upper()

	def _validar_codigos_unicos(self):
		vistos = {}
		for fila in self.codigos_oficiales or []:
			if not fila.codigo:
				continue
			if fila.codigo in vistos:
				frappe.throw(
					_("El código oficial {0} está repetido en las filas {1} y {2}.").format(
						frappe.bold(fila.codigo), vistos[fila.codigo], fila.idx
					),
					title=_("Código repetido"),
				)
			vistos[fila.codigo] = fila.idx

	def _validar_codigo_principal(self):
		"""El código principal tiene que ser uno de los declarados en la tabla.

		Si no, el programa publicaría hacia fuera un identificador que su propio
		detalle no respalda.
		"""
		if not self.codigo_oficial or not self.codigos_oficiales:
			return
		declarados = [f.codigo for f in self.codigos_oficiales if f.codigo]
		if self.codigo_oficial not in declarados:
			frappe.throw(
				_(
					"El código oficial {0} no figura en la tabla de códigos por modalidad. "
					"Agrégalo a la tabla o corrige el código principal."
				).format(frappe.bold(self.codigo_oficial)),
				title=_("Código principal sin respaldo"),
			)


def codigos_oficiales_de(programa: str) -> list[str]:
	"""Todos los códigos oficiales de un programa, en orden de captura.

	Lo usan los conectores que publican hacia sistemas externos: un programa puede
	responder a varios códigos y quedarse solo con el principal pierde las demás
	modalidades de la oferta.
	"""
	filas = frappe.get_all(
		"Codigo Oficial Programa",
		filters={"parent": programa, "parenttype": "Programa", "vigente": 1},
		fields=["codigo"],
		order_by="idx asc",
	)
	return [f.codigo for f in filas if f.codigo]
