# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Autoevaluacion(Document):
    def before_submit(self):
        """Congela el árbol del marco normativo justo antes del submit (Cerrada).

        Corre en el `_action == "submit"` de `run_before_save_methods` (ver
        `frappe/model/document.py`), es decir ANTES de que el docstatus quede
        persistido en 1 -- en ese instante el árbol vivo de Elemento Marco
        todavía es la fuente correcta a congelar. A partir de aquí
        `sgc.scoring` lee `marco_snapshot` en vez de consultar en vivo para
        esta autoevaluación, blindando el resultado contra ediciones
        posteriores del marco (reparenteos, correcciones de texto, etc.).
        """
        from sgc import scoring

        self.marco_snapshot = scoring.construir_snapshot(self.name)

    @frappe.whitelist()
    def datos_informe(self):
        """Contrato tipado del Informe de Autoevaluación (formato SINEACE).

        Devuelve exactamente `sgc.informe.consolidar(self.name)`: cabecera + estándares
        (nivel, semáforo, criterios, evidencias) + vigencia + matriz-resumen + anexo.

        Es el seam único de consumo del informe:
        - La plantilla Jinja del Print Format lo invoca con `doc.datos_informe()`.
        - Reservado como contrato MCP tipado (misma forma para la herramienta externa).

        Whitelisted para poder llamarse por API/plantilla; respeta permisos del doc.
        """
        from sgc.informe import consolidar

        return consolidar(self.name)

    @frappe.whitelist()
    def generar_pdf_informe(self, adjuntar=False):
        """Genera el PDF del informe (motor Chrome v16). Ver `sgc.informe.generar_pdf`.

        Con `adjuntar` truthy, lo guarda como File adjunto y devuelve {file_name, file_url}.
        """
        from sgc.informe import generar_pdf

        adjuntar = frappe.utils.cint(adjuntar)
        return generar_pdf(self.name, adjuntar=bool(adjuntar))
