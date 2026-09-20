"""Autorización mínima para servir el manual protegido mediante Caddy.

El endpoint no entrega identidad ni contenido: responde 204 cuando la sesión Frappe
está autenticada y redirige al login con un destino fijo cuando es Guest.

⚠️ ESTE MÓDULO NO ES CÓDIGO MUERTO, AUNQUE NADA DEL REPOSITORIO LO LLAME.

Su único consumidor está **fuera** del repositorio: el `forward_auth` de Caddy, que
consulta `/api/method/sgc.manual_auth.authorize` antes de servir `/manual`. Buscar
referencias dentro del código no encuentra ninguna, y por eso ya se borró una vez
—en `37221cd`, la limpieza de los módulos que solo servían a la SPA, donde este no
pintaba nada—. El manual quedó devolviendo **417** durante tres semanas sin que nada
lo señalara: el sitio respondía, el contenedor del manual seguía sano, y lo único
roto era la autorización (issue #67).

Si alguna vez deja de hacer falta, se retira **primero** el `forward_auth` del
Caddyfile y este módulo después. Al revés, el manual se cae.
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
