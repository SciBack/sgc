"""Cada módulo que declara el app existe como Module Def y tiene su área en el Desk."""

import frappe
from frappe.tests import IntegrationTestCase

from sgc import escritorio
from sgc.patches import modulos_por_area

# Pantallas que no van en ningún menú, a conciencia: se gestionan desde otra.
FUERA_DE_MENUS = {"Trazabilidad"}


def _destinos(tipos=("DocType", "Report")):
	return [
		(modulo, etiqueta, destino)
		for modulo, menu in escritorio.menus().items()
		for etiqueta, tipo, destino in escritorio.destinos(menu)
		if tipo in tipos
	]


class IntegrationTestModulosPorArea(IntegrationTestCase):
	def test_cada_modulo_declarado_existe(self):
		modulos_por_area.execute()
		for modulo in frappe.get_module_list("sgc"):
			self.assertTrue(frappe.db.exists("Module Def", modulo), modulo)

	def test_cada_modulo_es_un_area(self):
		self.assertEqual(set(frappe.get_module_list("sgc")), set(escritorio.areas()))

	def test_cada_pantalla_vive_en_su_area(self):
		"""Ninguna pantalla aparece en el menú de un área que no es la de su módulo."""
		for modulo, _etiqueta, destino in _destinos():
			tipo = "Report" if frappe.db.exists("Report", destino) else "DocType"
			self.assertEqual(frappe.db.get_value(tipo, destino, "module"), modulo, f"{destino} en {modulo}")

	def test_cada_pantalla_esta_en_un_menu_y_solo_en_uno(self):
		# Un menú por pantalla; dos accesos dentro del MISMO menú (una lista filtrada) no cuentan doble.
		en_menus = [destino for _m, destino in {(m, d) for m, _e, d in _destinos()}]
		self.assertEqual(sorted({x for x in en_menus if en_menus.count(x) > 1}), [])
		modulos = frappe.get_module_list("sgc")
		pantallas = set(frappe.get_all("DocType", filters={"module": ["in", modulos], "istable": 0}, pluck="name"))
		informes = set(frappe.get_all("Report", filters={"module": ["in", modulos]}, pluck="name"))
		self.assertEqual((pantallas | informes) - set(en_menus) - FUERA_DE_MENUS, set())

	def test_cada_pantalla_tiene_nombre_en_el_menu(self):
		for _modulo, etiqueta, destino in _destinos():
			self.assertTrue(etiqueta, destino)
