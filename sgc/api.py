"""API pública del SGC-UPeU."""

import frappe
from frappe.utils.oauth import get_oauth2_authorize_url

# Proveedor OIDC nativo (Social Login Key name == "keycloak") → IdP MicrosoftUPeU.
_PROVIDER = "keycloak"


@frappe.whitelist(allow_guest=True)
def acceso_m365(redirect_to: str = "/sgc/"):
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
        _PROVIDER, redirect_to or "/sgc/"
    )


@frappe.whitelist()
def get_niveles_escala():
    """Catálogo completo de "Nivel Escala" (NL/L/LP) con etiqueta legible.

    "Nivel Escala" quedó marcado `istable=1` en su DocType (diseño heredado);
    eso hace que los endpoints genéricos de listado/búsqueda de Frappe
    (frappe.client.get_list, frappe.desk.search.search_link) le recorten los
    campos extra y solo devuelvan `name` — es una limitación conocida del
    query builder de Frappe para doctypes de tabla consultados como si fueran
    documentos independientes. frappe.get_all con ignore_permissions no pasa
    por esa ruta restringida, así que sí trae sigla/etiqueta.
    """
    return frappe.get_all(
        "Nivel Escala",
        fields=["name", "sigla", "etiqueta", "orden"],
        order_by="orden asc",
        ignore_permissions=True,
    )
