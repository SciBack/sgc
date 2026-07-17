# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M12 — Grupo de Interés.

Catálogo de los grupos de interés (stakeholders) a los que se aplican los
instrumentos de escucha del SGC: beneficiarios (estudiantes/egresados),
colaboradores (docentes/administrativos) y externos (empleadores/aliados).

El DocType no tiene campo `estado` (Select de flujo), así que NO lleva Workflow.
La validación es mínima: normaliza los identificadores de texto.
"""
import frappe
from frappe.model.document import Document


class GrupoInteres(Document):
    def validate(self):
        # Normaliza el código y el nombre (evita duplicados por espacios sueltos;
        # `codigo` es la clave natural del DocType — autoname field:codigo, unique).
        if self.codigo:
            self.codigo = self.codigo.strip()
        if self.nombre:
            self.nombre = self.nombre.strip()
