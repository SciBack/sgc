"""La entrada al Desk va al SGC (1.1.0). Sustituye a desk_home.js.

Frappe tiene su propio ajuste para esto: System Settings → «App por defecto»
(`frappe.apps.get_default_path`). Solo se fija si nadie lo ha decidido antes.
"""

import frappe


def execute():
	if not frappe.db.get_single_value("System Settings", "default_app"):
		frappe.db.set_single_value("System Settings", "default_app", "sgc")
