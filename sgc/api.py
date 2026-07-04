"""API pública del SGC-UPeU."""

import frappe
from frappe.utils.oauth import get_oauth2_authorize_url

# Proveedor OIDC nativo (Social Login Key name == "keycloak") → IdP MicrosoftUPeU.
_PROVIDER = "keycloak"


@frappe.whitelist(allow_guest=True)
def acceso_m365(redirect_to: str = "/app"):
    """Inicia el login M365 de un clic (OIDC Keycloak) sin pasar por /login.

    Genera la URL de autorización del proveedor `keycloak` (que en el realm
    upeu brokerea directo a Microsoft) y redirige el navegador allí. Si el
    proveedor no estuviera configurado, cae al /login estándar.
    """
    if not frappe.db.exists("Social Login Key", _PROVIDER):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
        return

    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = get_oauth2_authorize_url(
        _PROVIDER, redirect_to or "/app"
    )
