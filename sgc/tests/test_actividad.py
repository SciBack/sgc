# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de la actividad de los relacionados en el timeline (`sgc/actividad.py`).

Cubre que el timeline de una no conformidad recoge el alta, los cambios de estado y
los comentarios de sus acciones de mejora; que va por el hook nativo
`additional_timeline_content`; que escapa lo que escribe la gente (el Desk lo inserta
como HTML); que no enseña acciones de otra NC; y que quien no puede leer acciones de
mejora no las ve.
"""

import frappe
from frappe.desk.form.load import get_additional_timeline_content
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc import actividad
from sgc.tests import factories

ADMIN = "Administrator"


class IntegrationTestActividad(IntegrationTestCase):
	def setUp(self):
		factories.desactivar_workflow("No Conformidad")
		factories.desactivar_workflow("Accion Mejora")
		self.addCleanup(frappe.set_user, ADMIN)
		self.nc = self._nc()
		self.accion = self._accion(self.nc.name)

	def _nc(self):
		return frappe.get_doc({
			"doctype": "No Conformidad",
			"titulo": "NC de prueba del timeline",
			"tipo": "No conformidad menor",
			"estado": "Abierta",
		}).insert(ignore_permissions=True)

	def _accion(self, nc):
		return frappe.get_doc({
			"doctype": "Accion Mejora",
			"descripcion": "Acción de prueba del timeline",
			"tipo": "Correctiva",
			"estado": "Planificada",
			"responsable": ADMIN,
			"no_conformidad": nc,
			"fecha_compromiso": add_days(nowdate(), 30),
		}).insert(ignore_permissions=True)

	def _contenidos(self, nc=None):
		return [e["content"] for e in actividad.timeline("No Conformidad", nc or self.nc.name)]

	def test_recoge_el_alta_el_cambio_de_estado_y_el_comentario(self):
		self.accion.add_comment("Workflow", "En ejecucion")
		self.accion.add_comment("Comment", "Ya se pidió el presupuesto")
		contenidos = self._contenidos()

		self.assertTrue(any("creó" in c and self.accion.name in c for c in contenidos))
		self.assertTrue(any("«En ejecucion»" in c for c in contenidos))
		self.assertTrue(any("Ya se pidió el presupuesto" in c for c in contenidos))

	def test_va_por_el_hook_nativo_del_formulario(self):
		self.assertIn("sgc.actividad.timeline",
					  frappe.get_hooks("additional_timeline_content").get("No Conformidad", []))
		entradas = get_additional_timeline_content("No Conformidad", self.nc.name)
		self.assertTrue(any(self.accion.name in e["content"] for e in entradas))
		for e in entradas:
			self.assertEqual(set(e), {"icon", "creation", "content"})

	def test_escapa_lo_que_escribe_la_gente(self):
		self.accion.add_comment("Comment", "<img src=x onerror=alert(1)> revisado")
		contenido = next(c for c in self._contenidos() if "revisado" in c)
		self.assertNotIn("<img", contenido)
		self.assertNotIn("onerror", contenido)

		# Así guarda el editor del Desk lo que alguien teclea: con entidades. Se muestra
		# escapado una sola vez, ni doble («&amp;lt;») ni como etiqueta de verdad.
		self.accion.add_comment("Comment", "<p>5 &lt; 7 &amp; &lt;b&gt;ojo&lt;/b&gt;</p>")
		contenido = next(c for c in self._contenidos() if "ojo" in c)
		self.assertIn("5 &lt; 7 &amp; &lt;b&gt;ojo&lt;/b&gt;", contenido)
		self.assertNotIn("&amp;lt;", contenido)

	def test_un_comentario_largo_se_recorta(self):
		self.accion.add_comment("Comment", "x" * 500)
		contenido = next(c for c in self._contenidos() if "xxxx" in c)
		self.assertIn("…", contenido)
		self.assertLess(contenido.count("x"), 260)

	def test_no_mezcla_acciones_de_otra_nc(self):
		otra = self._nc()
		ajena = self._accion(otra.name)
		self.assertFalse(any(ajena.name in c for c in self._contenidos()))

	def test_quien_no_puede_leer_acciones_no_las_ve(self):
		frappe.set_user("Guest")
		self.assertEqual(actividad.timeline("No Conformidad", self.nc.name), [])

	def test_el_plan_ve_sus_acciones(self):
		plan = frappe.get_doc({"doctype": "Plan Mejora", "titulo": "Plan de prueba del timeline",
							   "responsable": ADMIN}).insert(ignore_permissions=True, ignore_mandatory=True)
		frappe.db.set_value("Accion Mejora", self.accion.name, "plan_mejora", plan.name)
		self.assertTrue(any(self.accion.name in e["content"] for e in actividad.timeline("Plan Mejora", plan.name)))
