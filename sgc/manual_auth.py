"""Autorización mínima para servir el manual protegido mediante Caddy.

El endpoint no entrega identidad ni contenido: responde 204 cuando la sesión Frappe
está autenticada y redirige al login con un destino fijo cuando es Guest.
"""

import frappe


LOGIN_LOCATION = "/login?redirect-to=/manual/"
NO_STORE_HEADERS = {
    "Cache-Control": "no-store, private, max-age=0",
    "Pragma": "no-cache",
}


@frappe.whitelist(allow_guest=True)
def authorize():
    """Autoriza el subrequest de Caddy sin revelar datos de la sesión."""
    frappe.local.response["headers"] = NO_STORE_HEADERS.copy()

    if frappe.session.user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = LOGIN_LOCATION
        frappe.local.response["http_status_code"] = 302
        return None

    frappe.local.response["http_status_code"] = 204
    return None
