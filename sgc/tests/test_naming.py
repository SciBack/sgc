# Copyright (c) 2026, SciBack and contributors
# See license.txt
"""El correlativo cuenta lo que dice contar, y por prefijo.

Frappe resuelve cada `{parámetro}` de un `autoname` de tipo `format:` por
separado, así que el bloque de almohadillas pide `getseries("")`: un contador
GLOBAL del sitio. Se veía en los códigos emitidos, consecutivos entre tipos
distintos (`RSK-2026-00034`, `NC-2026-00035`, `TRR-2026-00036`). Ver
`sgc/naming.py`.
"""
import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestCorrelativoPorPrefijo(IntegrationTestCase):
	@staticmethod
	def _riesgo(titulo="Riesgo de prueba de naming"):
		doc = frappe.get_doc({"doctype": "Riesgo", "titulo": titulo})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		return doc

	@staticmethod
	def _no_conformidad():
		doc = frappe.get_doc({"doctype": "No Conformidad", "titulo": "NC de prueba de naming"})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		return doc

	def test_cada_doctype_lleva_su_propia_cuenta(self):
		"""Dos tipos distintos creados seguidos ya no comparten numeración.

		Antes salían consecutivos entre sí (RSK-…34, NC-…35) porque el contador
		era del sitio entero.
		"""
		riesgo = self._riesgo()
		nc = self._no_conformidad()
		self.assertTrue(riesgo.name.startswith("RSK-"))
		self.assertTrue(nc.name.startswith("NC-"))
		n_riesgo = int(riesgo.name.split("-")[-1])
		n_nc = int(nc.name.split("-")[-1])
		otro_riesgo = self._riesgo()
		# el riesgo siguiente continúa la cuenta de los RIESGOS, sin enterarse
		# de la no conformidad que se creó en medio
		self.assertEqual(int(otro_riesgo.name.split("-")[-1]), n_riesgo + 1)
		self.assertGreater(n_nc, 0)

	def test_correlativos_consecutivos_dentro_del_mismo_tipo(self):
		a = self._riesgo()
		b = self._riesgo()
		self.assertEqual(int(b.name.split("-")[-1]), int(a.name.split("-")[-1]) + 1)

	def test_conserva_la_forma_del_patron(self):
		"""El patrón del DocType manda en la forma: solo cambia de dónde sale el número."""
		sufijo = self._riesgo().name.split("-")[-1]
		self.assertEqual(len(sufijo), 5)  # RSK-{YYYY}-{#####}
		self.assertTrue(sufijo.isdigit())
