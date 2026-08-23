"""SGC SPA — punto de entrada. Sirve el bundle Vue/frappe-ui (www/sgc.html,
generado por `npm run build` en frontend/) para toda ruta bajo /sgc/* (ver
website_route_rules en hooks.py). El enrutado real lo hace vue-router en
el cliente; este handler solo inyecta el boot context (csrf_token, usuario).
"""

import frappe
from frappe.sessions import get_csrf_token

from sgc.permisos_ui import permisos_de_ui


def get_context(context):
	context.no_cache = 1

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/sgc"
		raise frappe.Redirect

	context.boot = {
		"csrf_token": get_csrf_token(),
		"user": frappe.session.user,
		"user_fullname": frappe.utils.get_fullname(frappe.session.user),
		"user_roles": frappe.get_roles(),
		# solo el admin (System Manager) ve el acceso al Escritorio (Desk)
		"is_system_manager": "System Manager" in frappe.get_roles(),
		# DocType -> {read, create, write, delete}: la SPA se pinta con esto en
		# vez de ofrecerle a todo el mundo el sistema entero. Va en el boot para
		# que no cueste una llamada extra. Ver sgc/permisos_ui.py.
		"permisos_ui": permisos_de_ui(),
	}
	return context
