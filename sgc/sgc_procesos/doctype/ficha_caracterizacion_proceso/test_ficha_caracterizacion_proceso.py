# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests del controlador de `Ficha Caracterizacion Proceso` (objetivo específico 3).

Lo que se verifica es la CADENA: declarar un indicador en la ficha debe dejar el
enlace explícito `Indicador.proceso` escrito (y quitarlo al dejar de declararlo),
y la ficha debe rechazar lo que rompería la distinción entre indicador de
proceso e indicador de acreditación.

Los helpers son privados de este módulo a propósito: `sgc/tests/factories.py` no
tiene factories de Indicador/Ficha y es un archivo compartido.
"""

import itertools

import frappe
from frappe.tests import IntegrationTestCase

from sgc.tests import factories

# Contador para códigos únicos dentro de la misma transacción de test
# (`Indicador.codigo` es unique y además es el autoname).
_seq = itertools.count(1)


EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


def _crear_indicador(categoria="Proceso", marco_normativo=None, proceso=None):
	"""Indicador mínimo con código único. Devuelve el Document."""
	codigo = "TEST-IND-{0:04d}".format(next(_seq))
	ind = frappe.get_doc({
		"doctype": "Indicador",
		"codigo": codigo,
		"nombre": "Indicador de prueba {0}".format(codigo),
		"categoria": categoria,
		"marco_normativo": marco_normativo,
		"proceso": proceso,
	})
	ind.flags.ignore_permissions = True
	ind.insert(ignore_permissions=True)
	return ind


def _crear_marco():
	"""Marco Normativo mínimo (idempotente por código) para marcar acreditación."""
	codigo = "TEST-MARCO-IND"
	if frappe.db.exists("Marco Normativo", codigo):
		return frappe.get_doc("Marco Normativo", codigo)
	marco = frappe.get_doc({
		"doctype": "Marco Normativo",
		"codigo": codigo,
		"nombre": "Marco de prueba para indicadores",
		"ente": "SINEACE",
		"estado": "vigente",
	})
	marco.flags.ignore_permissions = True
	marco.insert(ignore_permissions=True)
	return marco


def _crear_ficha(proceso, indicadores=None):
	"""Ficha de Caracterización con los indicadores declarados. Devuelve el doc."""
	ficha = frappe.get_doc({
		"doctype": "Ficha Caracterizacion Proceso",
		"proceso": proceso,
		"version": "1",
		"objetivo": "Objetivo de prueba",
		"indicadores": [{"indicador": i} for i in (indicadores or [])],
	})
	ficha.flags.ignore_permissions = True
	ficha.insert(ignore_permissions=True)
	return ficha


class IntegrationTestFichaCaracterizacionProceso(IntegrationTestCase):
	"""Integration tests for FichaCaracterizacionProceso."""

	def setUp(self):
		self.proceso = factories.crear_proceso().name

	# -------------------------------------------------------- sincronización

	def test_declarar_indicador_escribe_el_enlace_al_proceso(self):
		"""La ficha es lo que convierte un Indicador en indicador DE un proceso."""
		ind = _crear_indicador()
		self.assertFalse(ind.proceso)

		_crear_ficha(self.proceso, [ind.name])

		self.assertEqual(frappe.db.get_value("Indicador", ind.name, "proceso"), self.proceso)
		self.assertEqual(frappe.db.get_value("Indicador", ind.name, "categoria"), "Proceso")

	def test_sincronizacion_es_idempotente(self):
		"""Guardar N veces la misma ficha deja exactamente el mismo estado."""
		ind = _crear_indicador()
		ficha = _crear_ficha(self.proceso, [ind.name])

		ficha.save(ignore_permissions=True)
		ficha.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value("Indicador", ind.name, "proceso"), self.proceso)
		self.assertEqual(len(ficha.indicadores), 1)

	def test_quitar_la_fila_libera_el_indicador(self):
		"""Si la ficha deja de declararlo, el indicador deja de colgar del proceso."""
		ind = _crear_indicador()
		ficha = _crear_ficha(self.proceso, [ind.name])
		self.assertEqual(frappe.db.get_value("Indicador", ind.name, "proceso"), self.proceso)

		ficha.indicadores = []
		ficha.save(ignore_permissions=True)

		self.assertFalse(frappe.db.get_value("Indicador", ind.name, "proceso"))

	def test_no_toca_indicadores_de_otro_proceso(self):
		"""La limpieza solo alcanza a los indicadores del proceso de ESTA ficha."""
		otro_proceso = factories.crear_proceso().name
		ajeno = _crear_indicador()
		_crear_ficha(otro_proceso, [ajeno.name])

		propio = _crear_indicador()
		ficha = _crear_ficha(self.proceso, [propio.name])
		ficha.indicadores = []
		ficha.save(ignore_permissions=True)

		# El del otro proceso sigue intacto.
		self.assertEqual(frappe.db.get_value("Indicador", ajeno.name, "proceso"), otro_proceso)

	def test_borrar_la_ficha_libera_sus_indicadores(self):
		"""Sin ficha no hay declaración: ningún indicador queda apuntando al proceso."""
		ind = _crear_indicador()
		ficha = _crear_ficha(self.proceso, [ind.name])

		ficha.delete(ignore_permissions=True)

		self.assertFalse(frappe.db.get_value("Indicador", ind.name, "proceso"))

	# ------------------------------------------------------------ validaciones

	def test_rechaza_indicador_de_acreditacion(self):
		"""Un indicador con marco normativo NO es indicador de proceso (objetivo 3)."""
		marco = _crear_marco()
		ind = _crear_indicador(categoria="Acreditacion", marco_normativo=marco.name)

		with self.assertRaises(frappe.ValidationError):
			_crear_ficha(self.proceso, [ind.name])

	def test_rechaza_indicadores_duplicados_en_la_misma_ficha(self):
		"""El mismo indicador no puede declararse dos veces."""
		ind = _crear_indicador()

		with self.assertRaises(frappe.ValidationError):
			_crear_ficha(self.proceso, [ind.name, ind.name])

	def test_rechaza_indicador_ya_declarado_en_otra_ficha(self):
		"""Un indicador de desempeño pertenece a un solo proceso."""
		ind = _crear_indicador()
		_crear_ficha(self.proceso, [ind.name])

		otro_proceso = factories.crear_proceso().name
		with self.assertRaises(frappe.ValidationError):
			_crear_ficha(otro_proceso, [ind.name])
