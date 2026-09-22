# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Configuracion Correo — modo de ensayo y lista blanca de estreno (#41).

La lógica de envío está en `sgc.correo`; aquí solo se guarda y se valida.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address

from sgc.correo import REAL, normalizar_lista


class ConfiguracionCorreo(Document):
	def validate(self):
		correos = normalizar_lista(self.lista_blanca)
		invalidos = [c for c in correos if not validate_email_address(c)]
		if invalidos:
			frappe.throw(_("No son direcciones de correo válidas: {0}").format(", ".join(invalidos)))
		self.lista_blanca = "\n".join(correos)
		self._no_encender_de_golpe()

	def _no_encender_de_golpe(self):
		"""Pasar a Real y vaciar la lista blanca son dos actos, no uno.

		Si se hacen en el mismo guardado, el primer envío real va a todo el
		mundo sin haber pasado por el estreno con unos pocos, que es justo lo
		que la lista blanca existe para evitar.
		"""
		antes = self.get_doc_before_save()
		if not antes:
			return
		pasa_a_real = antes.modo != REAL and self.modo == REAL
		vacia_lista = bool(normalizar_lista(antes.lista_blanca)) and not self.lista_blanca
		if pasa_a_real and vacia_lista:
			frappe.throw(
				_(
					"Pasar a envío real y vaciar la lista blanca son dos pasos separados. "
					"Primero pase a Real con la lista blanca; cuando compruebe lo que llega, vacíela en otro guardado."
				),
				title=_("Dos pasos, no uno"),
			)
