# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Submit nativo (is_submittable) + captura del marco_snapshot al Cerrar.

`Autoevaluacion` tiene Workflow ACTIVO ("Autoevaluacion SGC", ver
`sgc/setup/f2_workflow.py`) y su estado final "Cerrada" mapea a
`doc_status="1"` -- la transición "Cerrar" dispara el submit NATIVO de Frappe
(docstatus 0->1) vía `frappe.model.workflow.apply_workflow`. Estos tests
recorren la cadena REAL de transiciones (NO `desactivar_workflow` -- eso
también desactiva el submit-por-workflow) y verifican que
`Autoevaluacion.before_submit` congeló el árbol del marco en `marco_snapshot`
con la estructura exacta del contrato (ver `sgc.scoring.construir_snapshot`).
"""
import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase

from sgc.tests import factories

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]

# Acciones del Workflow "Autoevaluacion SGC" en orden, hasta "Cerrada"
# (ver sgc/setup/f2_workflow.py WF_AUTOEVAL["transitions"]).
_CADENA_CIERRE = ("Iniciar evaluacion", "Enviar a revision", "Consolidar", "Cerrar")


def _cerrar_autoevaluacion(ae_name):
	"""Recorre la cadena REAL de transiciones del Workflow hasta 'Cerrada'.

	La última transición ('Cerrar', next_state doc_status='1') dispara
	`doc.submit()` dentro de `apply_workflow` -- ahí corre `before_submit` y
	se congela `marco_snapshot`. Devuelve el Document recargado (docstatus=1).
	"""
	doc = frappe.get_doc("Autoevaluacion", ae_name)
	for accion in _CADENA_CIERRE:
		doc = apply_workflow(doc, accion)
	doc.reload()
	return doc


class IntegrationTestAutoevaluacion(IntegrationTestCase):
	"""
	Integration tests for Autoevaluacion.
	Use this class for testing interactions between multiple components.
	"""

	def setUp(self):
		self.arbol = factories.crear_marco_prueba(n_estandares=2, n_criterios=2, prefijo="TESTSUB")
		self.marco = self.arbol["marco"]
		self.ae = factories.crear_autoevaluacion(self.arbol, prefijo="TESTSUB").name

	def test_cerrar_dispara_submit_nativo_y_congela_snapshot(self):
		doc = _cerrar_autoevaluacion(self.ae)

		# a) el submit nativo quedó disparado por la transición "Cerrar".
		self.assertEqual(doc.estado, "Cerrada")
		self.assertEqual(doc.docstatus, 1)

		# b) marco_snapshot quedó poblado con la estructura EXACTA del contrato.
		snap = doc.marco_snapshot
		if isinstance(snap, str):
			snap = frappe.parse_json(snap)
		self.assertIsInstance(snap, dict)
		self.assertEqual(
			set(snap.keys()),
			{"tomado_en", "marco_normativo", "escala_valoracion", "niveles", "elementos"},
		)
		self.assertEqual(snap["marco_normativo"], self.marco)
		self.assertTrue(snap["tomado_en"])

		# niveles: los 3 Nivel Escala NL/L/LP de la escala de prueba.
		self.assertEqual({n["sigla"] for n in snap["niveles"]}, {"NL", "L", "LP"})
		for n in snap["niveles"]:
			self.assertIn("score", n)
			self.assertIn("orden", n)
			self.assertIn("es_aprobatorio", n)

		# elementos: dict indexado por name, con los 2 estándares + 4 criterios
		# (2 estándares x 2 criterios) del árbol de prueba.
		self.assertEqual(len(snap["elementos"]), 2 + 2 * 2)
		for est in self.arbol["estandares"]:
			self.assertIn(est, snap["elementos"])
			el = snap["elementos"][est]
			self.assertEqual(el["tipo"], "Estandar")
			self.assertIsNone(el["parent_elemento_marco"])
		for est, crits in self.arbol["criterios"].items():
			for cr in crits:
				self.assertIn(cr, snap["elementos"])
				el = snap["elementos"][cr]
				self.assertEqual(el["tipo"], "Criterio")
				self.assertEqual(el["es_valorable"], 1)
				self.assertEqual(el["parent_elemento_marco"], est)

	def test_autoevaluacion_draft_no_es_submittable_todavia(self):
		# Antes de recorrer la cadena, sigue en Draft (docstatus=0), sin snapshot.
		doc = frappe.get_doc("Autoevaluacion", self.ae)
		self.assertEqual(doc.docstatus, 0)
		self.assertFalse(doc.marco_snapshot)
