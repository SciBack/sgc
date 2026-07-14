# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Vínculo N:M entre una Evidencia y un Elemento del Marco (M09).

Elemento Marco es el árbol normativo completo: cubre estándares, criterios,
indicadores y condiciones (CBC). Una misma evidencia puede respaldar varios
elementos, y un elemento se sustenta en varias evidencias (relación N:M que
exigen los modelos SINEACE). Es una tabla hija usada como Table MultiSelect.
"""

from frappe.model.document import Document


class EvidenciaElemento(Document):
	pass
