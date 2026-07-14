# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Fila del historial de cambios de un Documento Controlado (M03).

Registra qué cambió en cada versión publicada (Versión / Sección / Descripción),
como exige ISO 21001 cl. 7.5.3.2.d. Es una tabla hija: el controlador de
Documento Controlado la puebla al publicar; el usuario no la edita a mano.
"""

from frappe.model.document import Document


class CambioDocumento(Document):
	pass
