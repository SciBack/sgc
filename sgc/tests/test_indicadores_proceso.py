# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.indicadores_proceso` — indicadores de desempeño por proceso.

Cubre el contrato del motor lector del objetivo específico 3:
- solo entra lo que tiene enlace EXPLÍCITO (ficha → indicador); nada se infiere;
- lo que no entra se REPORTA en `omitidos` con su razón (no se calla ni se adivina);
- la última medición es la de mayor `fecha`, con su meta/unidad de Ficha Indicador;
- los indicadores de acreditación quedan fuera aunque el dato histórico los cuele.
"""

import itertools

import frappe
from frappe.tests import IntegrationTestCase

from sgc.indicadores_proceso import (
	OMITIDO_INDICADOR_ACREDITACION,
	OMITIDO_INDICADOR_INEXISTENTE,
	OMITIDO_SIN_FICHA,
	OMITIDO_SIN_INDICADORES,
	OMITIDO_SIN_MEDICION,
	filas_por_proceso,
	indicadores_de_proceso,
	tablero_indicadores_proceso,
)
from sgc.tests import factories

_seq = itertools.count(1)


def _crear_indicador():
	"""Indicador de proceso mínimo, con código único por transacción."""
	codigo = "TEST-IP-{0:04d}".format(next(_seq))
	ind = frappe.get_doc({
		"doctype": "Indicador",
		"codigo": codigo,
		"nombre": "Indicador de proceso {0}".format(codigo),
		"categoria": "Proceso",
	})
	ind.flags.ignore_permissions = True
	ind.insert(ignore_permissions=True)
	return ind


def _crear_ficha(proceso, indicadores=None):
	ficha = frappe.get_doc({
		"doctype": "Ficha Caracterizacion Proceso",
		"proceso": proceso,
		"version": "1",
		"indicadores": [{"indicador": i} for i in (indicadores or [])],
	})
	ficha.flags.ignore_permissions = True
	ficha.insert(ignore_permissions=True)
	return ficha


def _crear_ficha_indicador(indicador, valor_referencial=None, unidad="%"):
	doc = frappe.get_doc({
		"doctype": "Ficha Indicador",
		"indicador": indicador,
		"tipo_valor": "porcentaje",
		"unidad": unidad,
		"valor_referencial": valor_referencial,
		"frecuencia": "anual",
	})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc


def _crear_valor(indicador, valor_num, fecha):
	doc = frappe.get_doc({
		"doctype": "Valor Indicador",
		"indicador": indicador,
		"valor_num": valor_num,
		"fecha": fecha,
	})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc


def _razones(omitidos, proceso):
	return {o["razon"] for o in omitidos if o["proceso"] == proceso}


class IntegrationTestIndicadoresProceso(IntegrationTestCase):
	def setUp(self):
		self.proceso = factories.crear_proceso().name

	# ------------------------------------------------------------- omisiones

	def test_proceso_sin_ficha_se_omite_y_se_reporta(self):
		"""Sin ficha no hay declaración: cero indicadores y razón explícita."""
		datos = indicadores_de_proceso(self.proceso)
		self.assertEqual(datos["indicadores"], [])
		self.assertIn(OMITIDO_SIN_FICHA, _razones(datos["omitidos"], self.proceso))

	def test_ficha_sin_indicadores_se_reporta(self):
		"""La ficha existe pero no declara nada: se distingue de 'no hay ficha'."""
		_crear_ficha(self.proceso)
		datos = indicadores_de_proceso(self.proceso)
		self.assertEqual(datos["indicadores"], [])
		self.assertIn(OMITIDO_SIN_INDICADORES, _razones(datos["omitidos"], self.proceso))

	def test_indicador_sin_medicion_aparece_pero_se_reporta(self):
		"""Declarado pero nunca medido: sale en la fila con medido=False y se reporta."""
		ind = _crear_indicador()
		_crear_ficha(self.proceso, [ind.name])

		datos = indicadores_de_proceso(self.proceso)
		self.assertEqual(len(datos["indicadores"]), 1)
		fila = datos["indicadores"][0]
		self.assertEqual(fila["indicador"], ind.name)
		self.assertFalse(fila["medido"])
		self.assertIsNone(fila["cumple_meta"])
		self.assertIn(OMITIDO_SIN_MEDICION, _razones(datos["omitidos"], self.proceso))

	def test_indicador_borrado_se_omite_sin_romper(self):
		"""Link roto: se reporta como inexistente, nunca se adivina por texto."""
		ind = _crear_indicador()
		_crear_ficha(self.proceso, [ind.name])
		# force=True para saltar el chequeo de enlaces: simula un borrado directo.
		frappe.delete_doc("Indicador", ind.name, force=True, ignore_permissions=True)

		datos = indicadores_de_proceso(self.proceso)
		self.assertEqual(datos["indicadores"], [])
		self.assertIn(OMITIDO_INDICADOR_INEXISTENTE, _razones(datos["omitidos"], self.proceso))

	def test_indicador_de_acreditacion_queda_fuera(self):
		"""Dato histórico: si el indicador tiene marco normativo, no es de proceso."""
		ind = _crear_indicador()
		_crear_ficha(self.proceso, [ind.name])
		# El marco se pone DESPUÉS de guardar la ficha: la validación de la ficha
		# impide declararlo, pero un dato cargado antes de esa regla sí puede existir.
		marco = self._marco()
		frappe.db.set_value("Indicador", ind.name, "marco_normativo", marco, update_modified=False)

		datos = indicadores_de_proceso(self.proceso)
		self.assertEqual(datos["indicadores"], [])
		self.assertIn(
			OMITIDO_INDICADOR_ACREDITACION, _razones(datos["omitidos"], self.proceso)
		)

	# --------------------------------------------------------------- lectura

	def test_toma_la_ultima_medicion_por_fecha(self):
		"""De varias mediciones, la fila trae la más reciente."""
		ind = _crear_indicador()
		_crear_ficha(self.proceso, [ind.name])
		_crear_valor(ind.name, 40.0, "2026-01-15 09:00:00")
		_crear_valor(ind.name, 72.5, "2026-06-30 09:00:00")

		fila = indicadores_de_proceso(self.proceso)["indicadores"][0]
		self.assertTrue(fila["medido"])
		self.assertEqual(fila["valor_num"], 72.5)

	def test_meta_y_unidad_vienen_de_la_ficha_indicador(self):
		"""La semántica de medición (meta, unidad) es la de `Ficha Indicador`."""
		ind = _crear_indicador()
		_crear_ficha(self.proceso, [ind.name])
		_crear_ficha_indicador(ind.name, valor_referencial=60.0, unidad="%")
		_crear_valor(ind.name, 72.5, "2026-06-30 09:00:00")

		fila = indicadores_de_proceso(self.proceso)["indicadores"][0]
		self.assertEqual(fila["meta"], 60.0)
		self.assertEqual(fila["unidad"], "%")
		self.assertTrue(fila["cumple_meta"])

	def test_incumplimiento_de_meta(self):
		"""Por debajo del umbral, `cumple_meta` es False (no None)."""
		ind = _crear_indicador()
		_crear_ficha(self.proceso, [ind.name])
		_crear_ficha_indicador(ind.name, valor_referencial=60.0)
		_crear_valor(ind.name, 41.0, "2026-06-30 09:00:00")

		fila = indicadores_de_proceso(self.proceso)["indicadores"][0]
		self.assertFalse(fila["cumple_meta"])

	def test_sin_meta_no_se_emite_juicio(self):
		"""Sin `valor_referencial` no se inventa un umbral: cumple_meta es None."""
		ind = _crear_indicador()
		_crear_ficha(self.proceso, [ind.name])
		_crear_ficha_indicador(ind.name, valor_referencial=None)
		_crear_valor(ind.name, 41.0, "2026-06-30 09:00:00")

		fila = indicadores_de_proceso(self.proceso)["indicadores"][0]
		self.assertIsNone(fila["cumple_meta"])

	def test_filtro_por_proceso_no_trae_otros(self):
		"""`filas_por_proceso` acotado devuelve solo los procesos pedidos."""
		otro = factories.crear_proceso().name
		datos = filas_por_proceso(procesos=[self.proceso])
		codigos = {p["proceso"] for p in datos["procesos"]}
		self.assertIn(self.proceso, codigos)
		self.assertNotIn(otro, codigos)

	# --------------------------------------------------------------- tablero

	def test_totales_del_tablero_son_consistentes(self):
		"""Los totales cuadran con las filas: no hay conteo por fuera del dato."""
		ind = _crear_indicador()
		_crear_ficha(self.proceso, [ind.name])
		_crear_ficha_indicador(ind.name, valor_referencial=60.0)
		_crear_valor(ind.name, 72.5, "2026-06-30 09:00:00")

		datos = tablero_indicadores_proceso()
		totales = datos["totales"]
		self.assertEqual(totales["procesos"], len(datos["procesos"]))
		self.assertEqual(
			totales["indicadores"],
			sum(len(p["indicadores"]) for p in datos["procesos"]),
		)
		self.assertEqual(
			totales["indicadores_medidos"] + totales["indicadores_sin_medicion"],
			totales["indicadores"],
		)
		# El proceso de este test aporta su indicador medido y cumpliendo meta.
		mio = [p for p in datos["procesos"] if p["proceso"] == self.proceso][0]
		self.assertEqual(len(mio["indicadores"]), 1)
		self.assertGreaterEqual(totales["indicadores_cumplen_meta"], 1)

	# ---------------------------------------------------------------- helper

	def _marco(self):
		"""Marco Normativo mínimo (idempotente) para marcar acreditación."""
		codigo = "TEST-MARCO-IP"
		if not frappe.db.exists("Marco Normativo", codigo):
			doc = frappe.get_doc({
				"doctype": "Marco Normativo",
				"codigo": codigo,
				"nombre": "Marco de prueba indicadores proceso",
				"ente": "SINEACE",
				"estado": "vigente",
			})
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
		return codigo
