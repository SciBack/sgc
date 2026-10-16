# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Escalar un hallazgo de autoevaluación a no conformidad desde la pantalla.

Hasta la 1.7.2 el método existía y estaba probado en `capa.py`, pero no tenía
botón: desde el Desk no había forma de escalar. Y como Frappe solo pide LECTURA
del hallazgo para llamar a un método del documento, abrirlo tal cual habría dejado
crear no conformidades a cualquiera que pudiera leerlo.
"""

import frappe
from frappe.tests import IntegrationTestCase

LECTOR = "lector-hallazgo@sgc-prueba-hallazgo.example.com"


class IntegrationTestHallazgo(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		if not frappe.db.exists("User", LECTOR):
			u = frappe.get_doc({"doctype": "User", "email": LECTOR, "first_name": "Lector",
			                    "send_welcome_email": 0})
			u.append("roles", {"role": "Decano/Director (lectura)"})
			u.insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _hallazgo(self, tipo="Debilidad"):
		doc = frappe.get_doc({
			"doctype": "Hallazgo",
			"tipo": tipo,
			"origen": "Autoevaluacion",
			"descripcion": "Hallazgo de prueba del escalado.",
		})
		doc.insert(ignore_permissions=True)
		return doc

	def test_escalar_crea_la_nc_y_marca_el_hallazgo(self):
		doc = self._hallazgo()

		nc = doc.escalar_a_no_conformidad()

		self.assertTrue(frappe.db.exists("No Conformidad", nc))
		doc.reload()
		self.assertEqual(doc.no_conformidad, nc)
		self.assertEqual(doc.escalado_a_nc, 1)
		self.assertEqual(frappe.db.get_value("No Conformidad", nc, "tipo"), "No conformidad menor")

	def test_escalar_es_idempotente(self):
		doc = self._hallazgo()

		primera = doc.escalar_a_no_conformidad()
		doc.reload()
		segunda = doc.escalar_a_no_conformidad()

		self.assertEqual(primera, segunda)

	def test_quien_no_puede_crear_nc_no_escala(self):
		"""Leer el hallazgo no basta: crear una NC es decisión de quien puede crearla."""
		doc = self._hallazgo()
		self.assertFalse(frappe.has_permission("No Conformidad", "create", user=LECTOR))

		frappe.set_user(LECTOR)
		with self.assertRaises(frappe.PermissionError):
			doc.escalar_a_no_conformidad()

		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value("Hallazgo", doc.name, "no_conformidad"))

	def test_una_fortaleza_no_escala(self):
		doc = self._hallazgo(tipo="Fortaleza")

		with self.assertRaises(frappe.ValidationError) as ctx:
			doc.escalar_a_no_conformidad()

		self.assertIn("no constituye una no conformidad", str(ctx.exception))
