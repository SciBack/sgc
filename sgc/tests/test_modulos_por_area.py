"""Cada módulo que declara el app existe como Module Def y tiene su área en el Desk."""

import frappe
from frappe.tests import IntegrationTestCase

from sgc.patches import modulos_por_area
from sgc.setup import f18_workspace


class IntegrationTestModulosPorArea(IntegrationTestCase):
	def test_cada_modulo_declarado_existe(self):
		modulos_por_area.execute()
		for modulo in frappe.get_module_list("sgc"):
			self.assertTrue(frappe.db.exists("Module Def", modulo), modulo)

	def test_cada_modulo_es_un_area(self):
		self.assertEqual(set(frappe.get_module_list("sgc")), set(f18_workspace.AREAS))

	def test_cada_pantalla_vive_en_su_area(self):
		"""Ninguna pantalla aparece en la barra de un área que no es la de su módulo."""
		for barra, items in f18_workspace.SIDEBARS.items():
			if barra == f18_workspace.WS:
				continue
			for _etiqueta, tipo, destino in items:
				if tipo in ("DocType", "Report") and frappe.db.exists(tipo, destino):
					self.assertEqual(frappe.db.get_value(tipo, destino, "module"), barra, f"{destino} en {barra}")

	def test_cada_pantalla_esta_en_un_menu_y_solo_en_uno(self):
		"""Ninguna pantalla del SGC queda sin menú, ni aparece en dos tarjetas."""
		en_tarjetas = [(x[1] if isinstance(x, tuple) else x) for v in f18_workspace.TARJETAS.values() for x in v]
		self.assertEqual(sorted({x for x in en_tarjetas if en_tarjetas.count(x) > 1}), [])
		modulos = frappe.get_module_list("sgc")
		pantallas = set(frappe.get_all("DocType", filters={"module": ["in", modulos], "istable": 0}, pluck="name"))
		informes = set(frappe.get_all("Report", filters={"module": ["in", modulos]}, pluck="name"))
		self.assertEqual((pantallas | informes) - set(en_tarjetas) - FUERA_DE_MENUS, set())

	def test_cada_pantalla_tiene_nombre_en_el_menu(self):
		for items in f18_workspace.TARJETAS.values():
			for x in items:
				nombre = x[1] if isinstance(x, tuple) else x
				self.assertIn(nombre, f18_workspace.ETIQUETAS, nombre)


# Pantallas que no van en ningún menú, a conciencia: se gestionan desde otra.
FUERA_DE_MENUS = {"Trazabilidad"}
