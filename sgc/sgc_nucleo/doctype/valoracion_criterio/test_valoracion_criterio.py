# Copyright (c) 2026, SciBack and Contributors
# See license.txt

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


def _cerrar_autoevaluacion(autoevaluacion):
	"""Recorre la cadena REAL de transiciones del workflow hasta dejar la
	Autoevaluacion en 'Cerrada' (docstatus=1).

	Un `.save()` normal con `estado` reasignado a mano NO dispara el submit --
	`Document.validate_workflow()` solo invoca `set_workflow_state_on_action`
	cuando `self._action != "save"` (confirmado leyendo
	frappe/model/workflow.py). El único camino real es
	`frappe.model.workflow.apply_workflow(doc, accion)`: para la transición
	cuyo next_state tiene doc_status="1" (aquí, "Cerrar" -> "Cerrada"), esa
	función llama `doc.submit()` explícitamente.

	Requiere que el Workflow 'Autoevaluacion SGC' siga ACTIVO (no llamar
	`factories.desactivar_workflow("Autoevaluacion")` antes de esto).
	Devuelve el doc recargado, ya con docstatus=1.
	"""
	name = autoevaluacion.name if hasattr(autoevaluacion, "name") else autoevaluacion
	doc = frappe.get_doc("Autoevaluacion", name)
	for accion in _CADENA_CIERRE:
		doc = apply_workflow(doc, accion)
	doc.reload()
	return doc


class IntegrationTestValoracionCriterio(IntegrationTestCase):
	"""
	Integration tests for ValoracionCriterio.
	Use this class for testing interactions between multiple components.
	"""

	def test_estado_se_deriva_del_juicio_y_no_del_cliente(self):
		"""El cliente solo expresa el juicio; el servidor gobierna el estado.

		Una valoración con juicio queda ``Valorado`` aunque el navegador intente
		mandar otro estado. Al retirar el juicio vuelve a ``Pendiente``.
		"""
		prefijo = "TESTVC0"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]

		vc = frappe.get_doc({
			"doctype": "Valoracion Criterio",
			"autoevaluacion": ae.name,
			"criterio": criterio,
			"cumple": "Cumple",
			"estado": "Revisado",
		}).insert(ignore_permissions=True)
		self.assertEqual(vc.estado, "Valorado")
		self.assertEqual(vc.valorado_por, "Administrator")
		self.assertTrue(vc.fecha)

		vc.cumple = None
		vc.estado = "En analisis"
		vc.save(ignore_permissions=True)
		self.assertEqual(vc.estado, "Pendiente")
		self.assertFalse(vc.valorado_por)
		self.assertFalse(vc.fecha)

	def test_valorar_criterio_en_borrador_funciona_normal(self):
		"""Con la Autoevaluacion en Planificada (docstatus=0), crear y editar una
		Valoracion Criterio funciona sin cambios de comportamiento (guard no aplica)."""
		prefijo = "TESTVC1"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]

		vc = factories.valorar_criterio(ae, criterio, cumple="Cumple")
		self.assertEqual(vc.cumple, "Cumple")

		# Reeditar (sigue en Planificada) -> no debe lanzar.
		vc.cumple = "No cumple"
		vc.save()
		self.assertEqual(
			frappe.db.get_value("Valoracion Criterio", vc.name, "cumple"), "No cumple"
		)

	def test_bloquea_edicion_de_valoracion_existente_tras_cierre(self):
		"""Tras recorrer la cadena real hasta 'Cerrada' (docstatus=1), editar una
		Valoracion Criterio ya existente de esa autoevaluacion lanza ValidationError."""
		prefijo = "TESTVC2"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]

		vc = factories.valorar_criterio(ae, criterio, cumple="Cumple")

		_cerrar_autoevaluacion(ae)

		vc.reload()
		vc.cumple = "No cumple"
		with self.assertRaises(frappe.ValidationError):
			vc.save()

	def test_bloquea_creacion_de_valoracion_nueva_tras_cierre(self):
		"""Tras el cierre, crear una Valoracion Criterio NUEVA ligada a esa
		autoevaluacion también lanza ValidationError (insert pasa por validate()
		igual que save(), es el mismo guard)."""
		prefijo = "TESTVC3"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		criterio = marco["criterios"][marco["estandares"][0]][0]

		_cerrar_autoevaluacion(ae)

		nueva = frappe.get_doc({
			"doctype": "Valoracion Criterio",
			"autoevaluacion": ae.name,
			"criterio": criterio,
			"cumple": "Cumple",
		})
		with self.assertRaises(frappe.ValidationError):
			nueva.insert()
