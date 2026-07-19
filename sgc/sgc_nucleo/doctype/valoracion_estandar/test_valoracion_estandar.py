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
# (ver sgc/setup/f2_workflow.py WF_AUTOEVAL["transitions"]). Duplicado a
# propósito respecto a `test_valoracion_criterio.py`: cada test file vive en
# el alcance de este agente, sin tocar `sgc/tests/factories.py`.
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

	Requiere el Workflow 'Autoevaluacion SGC' ACTIVO (no llamar
	`factories.desactivar_workflow("Autoevaluacion")` antes). Devuelve el doc
	recargado (docstatus=1).
	"""
	name = autoevaluacion.name if hasattr(autoevaluacion, "name") else autoevaluacion
	doc = frappe.get_doc("Autoevaluacion", name)
	for accion in _CADENA_CIERRE:
		doc = apply_workflow(doc, accion)
	doc.reload()
	return doc


class IntegrationTestValoracionEstandar(IntegrationTestCase):
	"""
	Integration tests for ValoracionEstandar.
	Use this class for testing interactions between multiple components.
	"""

	def test_confirmar_estandar_en_borrador_funciona_normal(self):
		"""Con la Autoevaluacion en Planificada (docstatus=0), crear/editar una
		Valoracion Estandar funciona sin cambios de comportamiento (guard no aplica)."""
		prefijo = "TESTVE1"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		estandar = marco["estandares"][0]

		ve = factories.confirmar_estandar(ae, estandar, "L", prefijo=prefijo)
		self.assertEqual(ve.confirmado, 1)

		ve.justificacion = "ajuste en borrador"
		ve.save()
		self.assertEqual(
			frappe.db.get_value("Valoracion Estandar", ve.name, "justificacion"),
			"ajuste en borrador",
		)

	def test_bloquea_edicion_de_valoracion_existente_tras_cierre(self):
		"""Tras recorrer la cadena real hasta 'Cerrada' (docstatus=1), editar una
		Valoracion Estandar ya existente lanza ValidationError."""
		prefijo = "TESTVE2"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		estandar = marco["estandares"][0]

		ve = factories.confirmar_estandar(ae, estandar, "L", prefijo=prefijo)

		_cerrar_autoevaluacion(ae)

		ve.reload()
		ve.justificacion = "intento de correccion post-cierre"
		with self.assertRaises(frappe.ValidationError):
			ve.save()

	def test_bloquea_creacion_de_valoracion_nueva_tras_cierre(self):
		"""Tras el cierre, crear una Valoracion Estandar NUEVA ligada a esa
		autoevaluacion también lanza ValidationError (insert pasa por validate()
		igual que save(), es el mismo guard)."""
		prefijo = "TESTVE3"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		estandar = marco["estandares"][0]

		_cerrar_autoevaluacion(ae)

		nueva = frappe.get_doc({
			"doctype": "Valoracion Estandar",
			"autoevaluacion": ae.name,
			"elemento_marco": estandar,
		})
		with self.assertRaises(frappe.ValidationError):
			nueva.insert()

	def test_confirmar_nivel_bloqueado_tras_cierre(self):
		"""`sgc.confirmacion.confirmar_nivel` escribe `Valoracion Estandar.nivel`
		con `ignore_permissions=True`, pero el doc igual pasa por `validate()`
		(el guard no distingue el origen del save). Decisión de diseño: la
		confirmación humana del nivel oficial debe ocurrir ANTES de "Cerrar"
		(en el estado "Consolidada" -- ver `sgc/setup/f2_workflow.py`), nunca
		después; que quede bloqueada tras el cierre es correcto, no una regresión.
		"""
		from sgc import confirmacion

		prefijo = "TESTVE4"
		marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo=prefijo)
		ae = factories.crear_autoevaluacion(marco, prefijo=prefijo)
		estandar = marco["estandares"][0]

		_cerrar_autoevaluacion(ae)

		with self.assertRaises(frappe.ValidationError):
			confirmacion.confirmar_nivel(ae.name, estandar, "L")
