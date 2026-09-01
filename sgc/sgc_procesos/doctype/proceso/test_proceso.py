# Copyright (c) 2026, SciBack and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from sgc.sgc_procesos.doctype.proceso.proceso import (
	asegurar_macroproceso_raiz,
	restaurar_clasificacion_raiz,
)

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestProceso(IntegrationTestCase):
	"""
	Integration tests for Proceso.
	Use this class for testing interactions between multiple components.
	"""

	def _crear_proceso(self, codigo, **valores):
		doc = frappe.get_doc(
			{
				"doctype": "Proceso",
				"codigo": codigo,
				"proceso": valores.pop("proceso", "Proceso de prueba"),
				"nivel": valores.pop("nivel", "Soporte"),
				"estado": valores.pop("estado", "Vigente"),
				**valores,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def _valores_protegidos(self, name):
		return frappe.db.get_value(
			"Proceso",
			name,
			["proceso", "nivel", "estado", "parent_proceso", "is_group", "nivel_bpm"],
			as_dict=True,
		)

	def test_clasifica_raiz_existente_sin_cambiar_estado(self):
		proceso = self._crear_proceso("TEST-MP-CLAS", proceso="Macro oficial")
		estado = proceso.estado

		resultado = asegurar_macroproceso_raiz("TEST-MP-CLAS", "Macro oficial", "Soporte")

		proceso.reload()
		self.assertEqual((proceso.is_group, proceso.nivel_bpm), (1, "Macroproceso"))
		self.assertEqual(proceso.estado, estado)
		self.assertEqual(
			resultado,
			{
				"name": "TEST-MP-CLAS",
				"changed": True,
				"is_group": 1,
				"nivel_bpm": "Macroproceso",
			},
		)

	def test_clasificacion_es_idempotente(self):
		self._crear_proceso("TEST-MP-IDEM", proceso="Macro idempotente")
		asegurar_macroproceso_raiz("TEST-MP-IDEM", "Macro idempotente", "Soporte")

		resultado = asegurar_macroproceso_raiz("TEST-MP-IDEM", "Macro idempotente", "Soporte")

		self.assertFalse(resultado["changed"])

	def test_rechaza_denominacion_distinta_sin_alterar(self):
		proceso = self._crear_proceso("TEST-MP-DEN", proceso="Denominación registrada")
		antes = self._valores_protegidos(proceso.name)

		with self.assertRaises(frappe.ValidationError):
			asegurar_macroproceso_raiz(proceso.name, "Otra denominación", "Soporte")

		self.assertEqual(self._valores_protegidos(proceso.name), antes)

	def test_rechaza_categoria_distinta_sin_alterar(self):
		proceso = self._crear_proceso("TEST-MP-CAT", proceso="Macro categorizada")
		antes = self._valores_protegidos(proceso.name)

		with self.assertRaises(frappe.ValidationError):
			asegurar_macroproceso_raiz(proceso.name, "Macro categorizada", "Clave")

		self.assertEqual(self._valores_protegidos(proceso.name), antes)

	def test_rechaza_proceso_con_padre_sin_alterar(self):
		padre = self._crear_proceso("TEST-MP-PADRE", proceso="Padre", is_group=1)
		hijo = self._crear_proceso(
			"TEST-MP-HIJO",
			proceso="Hijo",
			parent_proceso=padre.name,
		)
		antes = self._valores_protegidos(hijo.name)

		with self.assertRaises(frappe.ValidationError):
			asegurar_macroproceso_raiz(hijo.name, "Hijo", "Soporte")

		self.assertEqual(self._valores_protegidos(hijo.name), antes)

	def test_rechaza_registro_inexistente_sin_crearlo(self):
		with self.assertRaises(frappe.DoesNotExistError):
			asegurar_macroproceso_raiz("TEST-MP-INEXISTENTE", "No existe", "Soporte")

		self.assertFalse(frappe.db.exists("Proceso", "TEST-MP-INEXISTENTE"))

	def test_restaura_clasificacion_y_preserva_estado(self):
		proceso = self._crear_proceso(
			"TEST-MP-REST",
			proceso="Macro restaurable",
			estado="Obsoleto",
			is_group=1,
		)

		resultado = restaurar_clasificacion_raiz(
			proceso.name,
			"Macro restaurable",
			"Soporte",
			0,
		)

		proceso.reload()
		self.assertEqual((proceso.is_group, proceso.nivel_bpm), (0, "Proceso"))
		self.assertEqual(proceso.estado, "Obsoleto")
		self.assertEqual(
			resultado,
			{
				"name": proceso.name,
				"changed": True,
				"is_group": 0,
				"nivel_bpm": "Proceso",
			},
		)

	def test_restauracion_es_idempotente(self):
		proceso = self._crear_proceso("TEST-MP-REST-ID", proceso="Raíz hoja")

		resultado = restaurar_clasificacion_raiz(
			proceso.name,
			"Raíz hoja",
			"Soporte",
			0,
		)

		self.assertFalse(resultado["changed"])

	def test_restauracion_aplica_las_mismas_precondiciones(self):
		proceso = self._crear_proceso("TEST-MP-REST-VAL", proceso="Raíz protegida")
		antes = self._valores_protegidos(proceso.name)

		with self.assertRaises(frappe.ValidationError):
			restaurar_clasificacion_raiz(
				proceso.name,
				"Denominación incorrecta",
				"Soporte",
				1,
			)

		self.assertEqual(self._valores_protegidos(proceso.name), antes)

	def test_restauracion_rechaza_clasificacion_invalida_sin_alterar(self):
		proceso = self._crear_proceso("TEST-MP-REST-TIPO", proceso="Raíz protegida")
		antes = self._valores_protegidos(proceso.name)

		with self.assertRaises(frappe.ValidationError):
			restaurar_clasificacion_raiz(
				proceso.name,
				"Raíz protegida",
				"Soporte",
				2,
			)

		self.assertEqual(self._valores_protegidos(proceso.name), antes)
