# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""El estado de un documento con flujo de aprobación lo cambia el flujo, no el formulario.

Encontrado en el recorrido del 14-oct-2026: «Estado» se veía como un desplegable editable;
elegir «Publicado» y guardar no hacía nada (Frappe lo ignora) y no decía por qué. Y el código
de un Documento Controlado era obligatorio aunque el sistema lo genera solo, así que el
formulario no dejaba guardar a quien no sabía qué código inventar.
"""

import frappe
from frappe.tests import IntegrationTestCase

from sgc import estandar


class IntegrationTestEstadoDeFlujo(IntegrationTestCase):
	def test_el_campo_de_estado_de_cada_flujo_es_de_solo_lectura(self):
		for wf in estandar.workflows().values():
			campo = frappe.get_meta(wf["document_type"]).get_field(wf["workflow_state_field"])
			with self.subTest(doctype=wf["document_type"]):
				self.assertTrue(campo.read_only, "el estado se cambia con el menú Acciones")

	def test_el_documento_se_guarda_sin_codigo_y_el_sistema_lo_pone(self):
		self.assertFalse(frappe.get_meta("Documento Controlado").get_field("codigo").reqd)
		proceso = frappe.get_doc({"doctype": "Proceso", "codigo": "TEST-EF-01"}).insert(ignore_permissions=True)
		doc = frappe.get_doc({"doctype": "Documento Controlado", "titulo": "Sin código",
							  "tipo_documento": "Procedimiento", "proceso": proceso.name}).insert(ignore_permissions=True)
		self.assertTrue(doc.codigo.startswith("TEST-EF-01-"))
		self.assertEqual(doc.name, doc.codigo)

	def test_fichas_y_procedimientos_se_aprueban_por_otra_persona(self):
		"""Recorrido 14-oct-2026: el dueño publicaba su propia ficha; no había flujo."""
		for doctype in ("Ficha Caracterizacion Proceso", "Procedimiento"):
			wf = estandar.workflow_de(doctype)
			with self.subTest(doctype=doctype):
				self.assertIsNotNone(wf)
				aprobar = [t for t in wf["transitions"] if t["action"] == "Aprobar"]
				self.assertTrue(aprobar and all(t["allowed"] == "DPGC" and not t["allow_self_approval"] for t in aprobar))
				self.assertNotIn("Dueño de Proceso", {t["allowed"] for t in wf["transitions"] if t["next_state"] in ("Aprobado", "Publicado")})
