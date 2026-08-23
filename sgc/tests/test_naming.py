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

from sgc.naming import siguiente_correlativo

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


class UnitTestSiguienteCorrelativo(IntegrationTestCase):
	"""La otra mitad de `sgc/naming.py`: el correlativo de los códigos legibles.

	Los DocTypes que se autonombran por `field:codigo` (documento controlado,
	programa/informe/hallazgo de auditoría) componen ese código a mano. La
	función vivía COPIADA literalmente en los cuatro controladores.
	"""

	def test_cuenta_desde_el_mayor_sufijo(self):
		self.assertEqual(siguiente_correlativo(["PGA-2026-0001", "PGA-2026-0007"]), 8)

	def test_lista_vacia_empieza_en_uno(self):
		self.assertEqual(siguiente_correlativo([]), 1)

	def test_ignora_lo_que_no_termina_en_numero(self):
		"""Un código escrito a mano sin sufijo no debe romper la cuenta."""
		self.assertEqual(siguiente_correlativo(["PGA-2026-0003", "PGA-ESPECIAL", None]), 4)

	def test_reutiliza_el_numero_de_lo_borrado(self):
		"""Y esto es lo que la separa del contador de `tabSeries`.

		Aquí el número sale de lo que existe AHORA, así que borrar el último lo
		devuelve al ruedo: un código que la gente teclea y busca no debe dejar
		huecos. `correlativo_por_prefijo` hace lo contrario a propósito — nunca
		reutiliza, porque un identificador de sistema que reaparece puede
		colisionar con referencias ya emitidas fuera.

		Si alguien unifica ambos mecanismos algún día, este test es el que
		avisa de que no son intercambiables.
		"""
		self.assertEqual(siguiente_correlativo(["DOC-001", "DOC-002"]), 3)
		self.assertEqual(siguiente_correlativo(["DOC-001"]), 2)

