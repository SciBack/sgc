# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Tests M01 — Informe de Cumplimiento (diagnóstico anual de las 8 CBC).

Cubre el controlador `informe_cumplimiento.py`:
- auto-poblado de las CBC (Estandar) del marco al guardar (A2);
- consolidación de conteos + semáforo global (Rojo / Ámbar / Verde);
- exigencia de justificación a toda CBC parcial o no cumplida (A4);
- bloqueo de "Presentado a SUNEDU" con CBC sin evaluar / sin condiciones;
- helper whitelisted `cbc_no_cumplidas`.

Cada test corre en su propia transacción con rollback automático, así que las
factories no limpian. El DocType se autonombra `IAC-{anio}`; por eso cada
informe creado dentro de un mismo test usa un `anio` distinto para no colisionar.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.tests import factories
from sgc.sgc_procesos.doctype.informe_cumplimiento import informe_cumplimiento as ic


class IntegrationTestInformeCumplimiento(IntegrationTestCase):
	def setUp(self):
		# Árbol con 8 Estandar (= las 8 CBC), sin criterios: el IAC evalúa CBC.
		self.arbol = factories.crear_marco_prueba(n_estandares=8, n_criterios=0)
		self.marco = self.arbol["marco"]
		self.estandares = self.arbol["estandares"]  # ["TEST-E1", ... "TEST-E8"]

	# ------------------------------------------------------------ helpers

	@staticmethod
	def _cond(condicion, cumple=None, justificacion=None):
		row = {"condicion": condicion}
		if cumple:
			row["cumple"] = cumple
		if justificacion is not None:
			row["justificacion"] = justificacion
		return row

	def _informe(self, anio, condiciones=None, estado="Borrador", con_marco=True):
		doc = frappe.new_doc("Informe Cumplimiento")
		doc.anio = anio
		doc.estado = estado
		if con_marco:
			doc.marco_normativo = self.marco
		for c in condiciones or []:
			doc.append("condiciones", c)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		return doc

	# ------------------------------------------------------------ auto-poblado

	def test_autopobla_las_cbc_del_marco(self):
		"""Sin condiciones y con marco: carga las 8 CBC (Estandar) del marco."""
		doc = self._informe(2001)
		self.assertEqual(len(doc.condiciones), 8)
		cargadas = {c.condicion for c in doc.condiciones}
		self.assertEqual(cargadas, set(self.estandares))
		# Recién autopobladas quedan SIN evaluar.
		self.assertTrue(all(not c.cumple for c in doc.condiciones))

	def test_autopoblado_respeta_el_orden(self):
		"""Se cargan por `orden asc` -> E1 primero, E8 último."""
		doc = self._informe(2002)
		self.assertEqual(doc.condiciones[0].condicion, self.estandares[0])
		self.assertEqual(doc.condiciones[-1].condicion, self.estandares[-1])

	def test_no_reautopobla_si_ya_hay_condiciones(self):
		"""Con condiciones cargadas a mano NO vuelve a poblar las 8."""
		doc = self._informe(
			2003,
			condiciones=[self._cond(self.estandares[0], factories.CUMPLE)],
		)
		self.assertEqual(len(doc.condiciones), 1)
		self.assertEqual(doc.condiciones[0].condicion, self.estandares[0])

	def test_no_autopobla_sin_marco(self):
		"""Sin marco no hay de dónde poblar: queda vacío y no revienta."""
		doc = self._informe(2004, con_marco=False)
		self.assertEqual(len(doc.condiciones), 0)

	# ------------------------------------------------------------ semáforo

	def test_semaforo_verde_todas_cumplen(self):
		conds = [self._cond(e, factories.CUMPLE) for e in self.estandares]
		doc = self._informe(2005, condiciones=conds)
		self.assertEqual(doc.semaforo, "Verde")
		self.assertEqual(doc.n_cumple, 8)
		self.assertEqual(doc.n_parcial, 0)
		self.assertEqual(doc.n_no_cumple, 0)

	def test_semaforo_ambar_alguna_parcial(self):
		"""Una parcial (con justificación) y el resto cumple -> Ámbar."""
		conds = [self._cond(e, factories.CUMPLE) for e in self.estandares]
		conds[3] = self._cond(self.estandares[3], factories.CUMPLE_PARCIAL, "brecha menor")
		doc = self._informe(2006, condiciones=conds)
		self.assertEqual(doc.semaforo, "Ámbar")
		self.assertEqual(doc.n_parcial, 1)
		self.assertEqual(doc.n_cumple, 7)

	def test_semaforo_rojo_domina_sobre_parcial(self):
		"""Un No cumple manda: Rojo aunque también haya parciales."""
		conds = [self._cond(e, factories.CUMPLE) for e in self.estandares]
		conds[1] = self._cond(self.estandares[1], factories.CUMPLE_PARCIAL, "parcial")
		conds[2] = self._cond(self.estandares[2], factories.NO_CUMPLE, "sin implementar")
		doc = self._informe(2007, condiciones=conds)
		self.assertEqual(doc.semaforo, "Rojo")
		self.assertEqual(doc.n_no_cumple, 1)
		self.assertEqual(doc.n_parcial, 1)

	def test_semaforo_vacio_con_cbc_sin_evaluar(self):
		"""Con CBC sin evaluar el semáforo queda en blanco (ni Verde ni Rojo)."""
		conds = [
			self._cond(self.estandares[0], factories.CUMPLE),
			self._cond(self.estandares[1], factories.CUMPLE),
			self._cond(self.estandares[2]),  # sin evaluar
		]
		doc = self._informe(2008, condiciones=conds)
		self.assertEqual(doc.semaforo, "")
		self.assertEqual(doc.n_cumple, 2)

	def test_semaforo_vacio_autopoblado(self):
		"""Recién autopoblado (todas sin evaluar) -> semáforo vacío, conteos 0."""
		doc = self._informe(2009)
		self.assertEqual(doc.semaforo, "")
		self.assertEqual(doc.n_cumple, 0)
		self.assertEqual(doc.n_no_cumple, 0)

	# ------------------------------------------------------------ justificación (A4)

	def test_exige_justificacion_a_parcial(self):
		conds = [self._cond(self.estandares[0], factories.CUMPLE_PARCIAL)]  # sin justificar
		with self.assertRaises(frappe.ValidationError):
			self._informe(2010, condiciones=conds)

	def test_exige_justificacion_a_no_cumple(self):
		conds = [self._cond(self.estandares[0], factories.NO_CUMPLE)]  # sin justificar
		with self.assertRaises(frappe.ValidationError):
			self._informe(2011, condiciones=conds)

	def test_justificacion_solo_espacios_no_vale(self):
		"""Una justificación en blanco (solo espacios) no cuenta como justificada."""
		conds = [self._cond(self.estandares[0], factories.NO_CUMPLE, "   ")]
		with self.assertRaises(frappe.ValidationError):
			self._informe(2012, condiciones=conds)

	def test_cumple_no_exige_justificacion(self):
		"""'Cumple' no necesita justificación: guarda sin problema."""
		conds = [self._cond(e, factories.CUMPLE) for e in self.estandares[:3]]
		doc = self._informe(2013, condiciones=conds)
		self.assertEqual(doc.n_cumple, 3)

	def test_no_cumple_con_justificacion_pasa(self):
		conds = [self._cond(self.estandares[0], factories.NO_CUMPLE, "plan de acción abierto")]
		doc = self._informe(2014, condiciones=conds)
		self.assertEqual(doc.semaforo, "Rojo")
		self.assertEqual(doc.n_no_cumple, 1)

	# ------------------------------------------------------------ presentación a SUNEDU

	def test_presentar_bloqueado_con_cbc_sin_evaluar(self):
		"""Presentar a SUNEDU con las 8 CBC autopobladas (sin evaluar) -> bloqueo."""
		with self.assertRaises(frappe.ValidationError):
			self._informe(2015, estado="Presentado a SUNEDU")

	def test_presentar_bloqueado_sin_condiciones(self):
		"""Presentar sin ninguna condición (sin marco que poblar) -> bloqueo."""
		with self.assertRaises(frappe.ValidationError):
			self._informe(2016, estado="Presentado a SUNEDU", con_marco=False)

	def test_presentar_ok_con_todas_evaluadas(self):
		"""Todas las CBC evaluadas -> se presenta a SUNEDU sin error."""
		conds = [self._cond(e, factories.CUMPLE) for e in self.estandares]
		doc = self._informe(2017, condiciones=conds, estado="Presentado a SUNEDU")
		self.assertEqual(doc.estado, "Presentado a SUNEDU")
		self.assertEqual(doc.semaforo, "Verde")

	def test_borrador_permite_cbc_sin_evaluar(self):
		"""En Borrador sí se permite dejar CBC sin evaluar (solo bloquea al presentar)."""
		doc = self._informe(2018)  # autopoblado, sin evaluar, estado Borrador
		self.assertEqual(doc.estado, "Borrador")
		self.assertEqual(len(doc.condiciones), 8)

	# ------------------------------------------------------------ helper cbc_no_cumplidas

	def test_cbc_no_cumplidas_lista_parcial_y_no_cumple(self):
		conds = [
			self._cond(self.estandares[0], factories.CUMPLE),
			self._cond(self.estandares[1], factories.CUMPLE_PARCIAL, "brecha"),
			self._cond(self.estandares[2], factories.NO_CUMPLE, "sin implementar"),
			self._cond(self.estandares[3], factories.CUMPLE),
		]
		doc = self._informe(2019, condiciones=conds)

		resultado = ic.cbc_no_cumplidas(doc.name)
		self.assertEqual(len(resultado), 2)
		condiciones = {r["condicion"] for r in resultado}
		self.assertEqual(condiciones, {self.estandares[1], self.estandares[2]})
		cumples = {r["cumple"] for r in resultado}
		self.assertEqual(cumples, {factories.CUMPLE_PARCIAL, factories.NO_CUMPLE})

	def test_cbc_no_cumplidas_vacio_si_todas_cumplen(self):
		conds = [self._cond(e, factories.CUMPLE) for e in self.estandares]
		doc = self._informe(2020, condiciones=conds)
		self.assertEqual(ic.cbc_no_cumplidas(doc.name), [])

	# ------------------------------------------------------------ datos_diagnostico (contrato PDF)

	def test_datos_diagnostico_consolida_cabecera_y_conteos(self):
		conds = [self._cond(e, factories.CUMPLE) for e in self.estandares]
		conds[0] = self._cond(self.estandares[0], factories.NO_CUMPLE, "brecha crítica")
		doc = self._informe(2021, condiciones=conds)

		datos = doc.datos_diagnostico()
		self.assertEqual(datos["anio"], 2021)
		self.assertEqual(datos["marco"], self.marco)
		self.assertEqual(datos["total"], 8)
		self.assertEqual(datos["n_no_cumple"], 1)
		self.assertEqual(datos["n_cumple"], 7)
		self.assertEqual(datos["semaforo"], "Rojo")
		self.assertEqual(len(datos["condiciones"]), 8)
