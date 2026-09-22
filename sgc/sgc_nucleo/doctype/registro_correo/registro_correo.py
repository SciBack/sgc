# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Registro Correo — lo que una regla habría enviado y no envió (#41).

Solo lo escribe `sgc.correo`: nadie lo crea a mano (`in_create`). Los correos
que sí salen ya quedan en la `Email Queue` de Frappe; aquí va lo que el modo de
ensayo o la lista blanca detuvieron, que de otro modo no dejaría rastro.
"""

from frappe.model.document import Document


class RegistroCorreo(Document):
	pass
