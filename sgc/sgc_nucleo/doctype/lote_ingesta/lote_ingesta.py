"""Registro auditable escrito exclusivamente por el servicio de ingesta."""
import frappe
from frappe.model.document import Document


class LoteIngesta(Document):
    def validate(self):
        from sgc.ingesta import en_ingesta
        if not en_ingesta():
            frappe.throw("El lote solo puede escribirse mediante la API de ingesta.")

    def on_trash(self):
        frappe.throw("Los lotes de ingesta se conservan para auditoría.")
