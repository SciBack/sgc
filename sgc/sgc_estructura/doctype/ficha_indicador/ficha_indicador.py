# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Ficha Indicador — ficha técnica 1:1 con Indicador (o, alternativa CBC, con
Elemento Marco). Fase 2 (2026-07-19, hallazgo): el JSON documentaba "1:1" y
"alternativa" pero no había ninguna validación — nada impedía crear dos fichas
para el mismo indicador, ni una ficha con ambos anclajes (o ninguno) a la vez.
"""
import frappe
from frappe import _
from frappe.model.document import Document


class FichaIndicador(Document):
    def validate(self):
        if bool(self.indicador) == bool(self.elemento_marco):
            frappe.throw(
                _("La ficha debe anclarse a exactamente uno: «Indicador» "
                  "(fichas CONEAU/institucionales) o «Elemento marco» "
                  "(alternativa para indicadores CBC) — no ambos, no ninguno.")
            )
