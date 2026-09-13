# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""El portal lee por método de MÓDULO, no por la API v2 de documento.

La v2 añade `frappe.response.docs` con el documento entero al lado del resultado
—46 campos de metadatos de persona medidos en el lab—, así que por bien que
proyecte el método, el canal publica lo que nadie pidió. Estos tests fijan que el
contrato del portal entrega solo lo proyectado, y que respeta el estado.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc import portal_publico
from sgc.tests import factories

# Claves que jamás deben viajar al portal: metadatos de Frappe y personas.
PROHIBIDAS = {
	"owner", "modified_by", "creation", "modified", "docstatus",
	"_user_tags", "_comments", "_assign", "_liked_by", "responsable",
}


def _fugas(obj, ruta=""):
	"""Rutas con datos que no deben salir.

	`responsable` es ambiguo y la distinción importa: en `registros` es un `Link` a
	`User` —una persona— y no puede salir; dentro de `tareas` es el CARRIL del BPMN
	—un cargo, «Jefe de Redes, Soporte y Laboratorios»— y es justo lo que hace útil
	el diagrama. Se excluye por ruta, no por nombre de campo.
	"""
	encontradas = []
	if isinstance(obj, dict):
		for clave, valor in obj.items():
			if clave in PROHIBIDAS and not (clave == "responsable" and ".tareas[" in ruta):
				encontradas.append(f"{ruta}.{clave}")
			encontradas += _fugas(valor, f"{ruta}.{clave}")
	elif isinstance(obj, list):
		for i, valor in enumerate(obj):
			encontradas += _fugas(valor, f"{ruta}[{i}]")
	return encontradas


class IntegrationTestPortalPublico(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.fichas = []

	def tearDown(self):
		for f in self.fichas:
			if frappe.db.exists("Ficha Caracterizacion Proceso", f):
				frappe.delete_doc("Ficha Caracterizacion Proceso", f, ignore_permissions=True, force=True)
		frappe.db.commit()

	def _ficha(self, estado="Publicado"):
		doc = frappe.get_doc({
			"doctype": "Ficha Caracterizacion Proceso",
			"proceso": factories.crear_proceso().name,
			"version": "1.0",
			"objetivo": "Probar el contrato del portal.",
			"estado": "Borrador",
		}).insert(ignore_permissions=True)
		self.fichas.append(doc.name)
		doc.append("registros", {"registro": "Bitácora", "responsable": frappe.session.user,
		                         "frecuencia_revision": "Mensual"})
		doc.append("entradas", {"insumo": "Solicitud", "proveedor": "Usuario"})
		doc.estado = estado
		doc.save(ignore_permissions=True)
		return doc

	def test_una_ficha_no_publicada_no_entrega_nada(self):
		doc = self._ficha(estado="Borrador")
		self.assertIsNone(
			portal_publico.ficha(doc.name),
			"el estado se comprueba aquí: el permiso de Frappe no lo mira",
		)

	def test_lo_que_entrega_no_lleva_metadatos_ni_personas(self):
		doc = self._ficha()
		datos = portal_publico.ficha(doc.name)
		self.assertIsNotNone(datos)
		fugas = _fugas(datos)
		self.assertEqual(fugas, [], f"el contrato del portal no puede llevar {fugas}")

	def test_entrega_el_contenido_util(self):
		"""Que esté limpio no puede significar que esté vacío."""
		doc = self._ficha()
		datos = portal_publico.ficha(doc.name)
		self.assertIn("proceso", datos)
		self.assertEqual([r["insumo"] for r in datos["entradas"]], ["Solicitud"])
		self.assertEqual([r["registro"] for r in datos["registros"]], ["Bitácora"])

	def test_es_metodo_de_modulo_no_de_documento(self):
		"""La razón de existir de este módulo.

		Un método de documento solo se alcanza por la API v2, que adjunta
		`response.docs` con el documento entero. Uno de módulo se llama por
		`/api/method/` y devuelve solo su resultado.
		"""
		self.assertIn(
			portal_publico.ficha, frappe.whitelisted,
			"sin estar whitelisted no es alcanzable por /api/method/",
		)
		self.assertFalse(
			hasattr(portal_publico.ficha, "__self__"),
			"si fuera un método ligado a un documento, se llamaría por la v2 — y esa "
			"adjunta response.docs con el documento entero",
		)
		self.assertEqual(
			portal_publico.ficha.__module__, "sgc.portal_publico",
			"tiene que vivir en un módulo, no en la clase del doctype",
		)
