"""SGC SPA — punto de entrada. Sirve el bundle Vue/frappe-ui (www/sgc.html,
generado por `npm run build` en frontend/) para toda ruta bajo /sgc/* (ver
website_route_rules en hooks.py). El enrutado real lo hace vue-router en
el cliente; este handler solo inyecta el boot context (csrf_token, usuario).
"""

import frappe
from frappe.sessions import get_csrf_token


def get_context(context):
	context.no_cache = 1

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/sgc"
		raise frappe.Redirect

	context.boot = {
		"csrf_token": get_csrf_token(),
		"user": frappe.session.user,
		"user_fullname": frappe.utils.get_fullname(frappe.session.user),
		# solo el admin (System Manager) ve el acceso al Escritorio (Desk)
		"is_system_manager": "System Manager" in frappe.get_roles(),
	}
	return context
