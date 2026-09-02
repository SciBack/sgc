# Copyright (c) 2026, SciBack and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from sgc.sgc_estructura.doctype.programa.programa import codigos_oficiales_de

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestPrograma(IntegrationTestCase):
	"""Códigos oficiales del programa: normalización, unicidad y coherencia."""

	def _programa(self, codigo, **extra):
		doc = frappe.get_doc(
			{
				"doctype": "Programa",
				"codigo": codigo,
				"nombre": extra.pop("nombre", f"Programa {codigo}"),
				"nivel": "pregrado",
				"estado": "activo",
				**extra,
			}
		)
		doc.insert(ignore_permissions=True)
		self.addCleanup(lambda: frappe.delete_doc("Programa", doc.name, force=True))
		return doc

	def test_programa_sin_codigo_oficial_sigue_siendo_valido(self):
		"""Un programa sin correspondencia verificada queda en blanco, no se inventa.

		Cuando el ente rector no contempla el programa, o hay dos candidatos y la
		decisión es de Calidad, el campo se deja vacío. Bloquearlo obligaría a
		asignar un código por parecido de nombre, que es justo lo que no debe pasar.
		"""
		doc = self._programa("TEST-SIN-COD")
		self.assertIsNone(doc.codigo_oficial or None)
		self.assertEqual(codigos_oficiales_de(doc.name), [])

	def test_normaliza_a_mayusculas_y_sin_espacios(self):
		doc = self._programa(
			"TEST-NORM",
			codigo_oficial="  p04 ",
			codigos_oficiales=[{"codigo": " p04 ", "modalidad": "Presencial"}],
		)
		self.assertEqual(doc.codigo_oficial, "P04")
		self.assertEqual(doc.codigos_oficiales[0].codigo, "P04")

	def test_varias_modalidades_conviven_bajo_un_solo_programa(self):
		"""Una disciplina, varios códigos: es el caso normal, no una anomalía."""
		doc = self._programa(
			"TEST-MULTI",
			codigo_oficial="P04",
			codigos_oficiales=[
				{"codigo": "P04", "modalidad": "Presencial"},
				{"codigo": "P05", "modalidad": "Semipresencial"},
				{"codigo": "P95", "modalidad": "A Distancia"},
			],
		)
		self.assertEqual(codigos_oficiales_de(doc.name), ["P04", "P05", "P95"])

	def test_rechaza_codigo_repetido_en_la_tabla(self):
		with self.assertRaises(frappe.ValidationError):
			self._programa(
				"TEST-DUP",
				codigos_oficiales=[
					{"codigo": "P04", "modalidad": "Presencial"},
					{"codigo": "P04", "modalidad": "A Distancia"},
				],
			)

	def test_rechaza_codigo_principal_que_no_esta_en_la_tabla(self):
		"""Publicar un identificador que el propio detalle no respalda es un error."""
		with self.assertRaises(frappe.ValidationError):
			self._programa(
				"TEST-INCOH",
				codigo_oficial="P99",
				codigos_oficiales=[{"codigo": "P04", "modalidad": "Presencial"}],
			)

	def test_codigo_principal_sin_tabla_es_valido(self):
		"""Cargar primero el código principal y detallar modalidades después."""
		doc = self._programa("TEST-SOLO-PRINCIPAL", codigo_oficial="P22")
		self.assertEqual(doc.codigo_oficial, "P22")

	def test_una_fila_no_vigente_no_se_publica_hacia_fuera(self):
		"""Un código retirado por resolución se conserva como histórico, no se borra."""
		doc = self._programa(
			"TEST-VIGENCIA",
			codigo_oficial="P04",
			codigos_oficiales=[
				{"codigo": "P04", "modalidad": "Presencial", "vigente": 1},
				{"codigo": "P05", "modalidad": "Semipresencial", "vigente": 0},
			],
		)
		self.assertEqual(codigos_oficiales_de(doc.name), ["P04"])
