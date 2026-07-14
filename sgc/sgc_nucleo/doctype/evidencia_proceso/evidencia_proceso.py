# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Vínculo N:M entre una Evidencia y un Proceso del Mapa (M09).

Permite que una evidencia se ancle a los procesos institucionales que sustenta
(RNF09: una evidencia debe poder vincularse a la vez a un proceso, una CBC y un
estándar). Tabla hija usada como Table MultiSelect.
"""

from frappe.model.document import Document


class EvidenciaProceso(Document):
	pass
