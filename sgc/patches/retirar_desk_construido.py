"""Quita los iconos de escritorio que creaba f18 para la miga de pan (1.1.0).

Hasta la 1.0.1, f18 creaba un Desktop Icon oculto por área solo para que la miga de pan
encontrara su título (lo necesitaba migas.js). Con los menús como ficheros estándar la miga
la resuelve Frappe, y esos iconos quedaban huérfanos. Solo se tocan los no estándar del SGC.
Las filas viejas de «Workspace Sidebar» se dejan: Frappe 16.50+ las guarda como archivo inerte.
"""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Desktop Icon"):
		return
	for nombre in frappe.get_all("Desktop Icon", filters={"app": "sgc", "standard": 0}, pluck="name"):
		frappe.delete_doc("Desktop Icon", nombre, force=1, ignore_permissions=True)
