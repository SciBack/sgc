# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""El PDF de la ficha se pregenera al publicar y se retira al despublicar.

Estas pruebas fijan el contrato que consume el portal público. Dos de ellas
existen por hallazgos concretos, no por completitud:

- El adjunto NO se acumula al republicar. Si se acumulara, quedaría descargable
  el PDF de una versión que ya no está vigente: los adjuntos de Frappe se sirven
  comprobando el permiso del DOCTYPE, nunca el estado del documento padre.
  Comprobado en el lab el 13-sep-2026 bajando el BPMN de un procedimiento en
  Borrador con el token del portal (HTTP 200).
- El nombre aguanta el sufijo hexadecimal que Frappe añade ante colisiones. Es
  el mismo fallo que hizo crecer sin fin los nombres de los .bpmn.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc import ficha_pdf
from sgc.tests import factories


class IntegrationTestFichaPDF(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.fichas = []

	def tearDown(self):
		for f in self.fichas:
			if frappe.db.exists("Ficha Caracterizacion Proceso", f):
				frappe.delete_doc("Ficha Caracterizacion Proceso", f, ignore_permissions=True, force=True)
		frappe.db.commit()

	# ------------------------------------------------------------------ puras

	def test_el_nombre_lleva_prefijo_propio(self):
		"""Sin prefijo, «el .pdf más reciente» sirve cualquier anexo que alguien suba."""
		self.assertEqual(ficha_pdf.nombre_pdf("FICHA-S04.01"), "ficha-FICHA-S04.01.pdf")

	def test_reconoce_su_pdf_aunque_frappe_le_ponga_sufijo(self):
		self.assertTrue(ficha_pdf.es_el_pdf("ficha-FICHA-S04.01.pdf", "FICHA-S04.01"))
		self.assertTrue(ficha_pdf.es_el_pdf("ficha-FICHA-S04.01a1b2c3.pdf", "FICHA-S04.01"))
		self.assertTrue(ficha_pdf.es_el_pdf("ficha-FICHA-S04.01a1b2c3d4e5f6.pdf", "FICHA-S04.01"))

	def test_no_confunde_un_anexo_con_su_pdf(self):
		"""El caso que rompe «el .pdf más reciente adjunto al documento»."""
		for ajeno in ("anexo-evidencia.pdf", "ficha-FICHA-S04.02.pdf", "informe.pdf", ""):
			with self.subTest(ajeno=ajeno):
				self.assertFalse(ficha_pdf.es_el_pdf(ajeno, "FICHA-S04.01"))

	def test_un_bpmn_no_es_el_pdf(self):
		self.assertFalse(ficha_pdf.es_el_pdf("ficha-FICHA-S04.01.bpmn", "FICHA-S04.01"))

	# ----------------------------------------------------------- integración

	def _ficha_publicada(self):
		proceso = factories.crear_proceso().name
		ficha = frappe.get_doc({
			"doctype": "Ficha Caracterizacion Proceso",
			"proceso": proceso,
			"version": "1.0",
			"objetivo": "Probar la pregeneración del PDF.",
			"estado": "Borrador",
		}).insert(ignore_permissions=True)
		self.fichas.append(ficha.name)
		return ficha

	def _pdfs_de(self, ficha):
		return [
			f.file_name
			for f in frappe.get_all(
				"File",
				filters={"attached_to_doctype": "Ficha Caracterizacion Proceso", "attached_to_name": ficha},
				fields=["file_name"],
			)
			if ficha_pdf.es_el_pdf(f.file_name, ficha)
		]

	def test_publicar_deja_el_pdf_y_despublicar_lo_retira(self):
		ficha = self._ficha_publicada()
		self.assertEqual(self._pdfs_de(ficha.name), [], "en Borrador no debe haber PDF")

		ficha.estado = "Publicado"
		ficha.save(ignore_permissions=True)
		self.assertEqual(len(self._pdfs_de(ficha.name)), 1, "publicar tiene que dejar el PDF hecho")

		ficha.estado = "Borrador"
		ficha.save(ignore_permissions=True)
		self.assertEqual(
			self._pdfs_de(ficha.name), [],
			"despublicar debe BORRAR el fichero: mientras exista se puede descargar",
		)

	def test_republicar_no_acumula_un_segundo_pdf(self):
		"""Acumular dejaría descargable el PDF de una versión ya no vigente."""
		ficha = self._ficha_publicada()
		for estado in ("Publicado", "Borrador", "Publicado", "Borrador", "Publicado"):
			ficha.estado = estado
			ficha.save(ignore_permissions=True)
		self.assertEqual(len(self._pdfs_de(ficha.name)), 1, "cada publicación reemplaza, no añade")

	def test_pdf_publicado_no_entrega_nada_si_no_esta_publicada(self):
		"""El contrato del portal: pregunta por la ficha, recibe el fichero o nada."""
		ficha = self._ficha_publicada()
		ficha.estado = "Publicado"
		ficha.save(ignore_permissions=True)
		self.assertIsNotNone(ficha_pdf.pdf_publicado(ficha.name))

		ficha.estado = "Borrador"
		ficha.save(ignore_permissions=True)
		self.assertIsNone(
			ficha_pdf.pdf_publicado(ficha.name),
			"una ficha no publicada no puede entregar su PDF por esta vía",
		)

	def test_borrar_la_ficha_no_deja_el_pdf_huerfano(self):
		ficha = self._ficha_publicada()
		ficha.estado = "Publicado"
		ficha.save(ignore_permissions=True)
		nombre = ficha.name
		self.assertEqual(len(self._pdfs_de(nombre)), 1)

		frappe.delete_doc("Ficha Caracterizacion Proceso", nombre, ignore_permissions=True, force=True)
		self.fichas.remove(nombre)
		self.assertEqual(self._pdfs_de(nombre), [], "el PDF no puede sobrevivir a su ficha")

	def test_un_fallo_al_renderizar_no_impide_guardar_la_ficha(self):
		"""El PDF es un derivado: perder el original por no poder dibujarlo sería
		el peor intercambio posible."""
		from unittest.mock import patch

		ficha = self._ficha_publicada()
		with patch.object(ficha_pdf, "_render", side_effect=RuntimeError("chrome no está")):
			ficha.estado = "Publicado"
			ficha.save(ignore_permissions=True)   # no debe propagar

		self.assertEqual(
			frappe.db.get_value("Ficha Caracterizacion Proceso", ficha.name, "estado"), "Publicado",
			"la ficha se guarda aunque su derivado falle",
		)

	def test_el_pdf_del_portal_no_lleva_nombres_de_personas(self):
		"""El agujero que la lista blanca de campos NO tapaba.

		El portal filtra qué campos expone, y `elaborado_por`/`revisado_por`/
		`aprobado_por` nunca estuvieron en esa lista. Daba igual: la plantilla
		institucional imprime los `full_name` de los tres, así que **el dato salía
		por el PDF**. Verificado en el lab el 13-sep-2026 sobre FICHA-S04.04.

		El PDF del portal usa la variante pública, que cita el ACTO (versión, fecha,
		estado, resolución) en vez de a las personas.
		"""
		import re

		ficha = self._ficha_publicada()
		nombres = {}
		for campo in ("elaborado_por", "revisado_por", "aprobado_por"):
			usuario = frappe.session.user
			ficha.set(campo, usuario)
			nombres[campo] = frappe.db.get_value("User", usuario, "full_name") or usuario
		ficha.estado = "Publicado"
		ficha.save(ignore_permissions=True)

		html = frappe.get_print(
			"Ficha Caracterizacion Proceso", ficha.name,
			print_format=ficha_pdf.PRINT_FORMAT, as_pdf=False,
		)
		texto = re.sub(r"<[^>]+>", " ", html)
		for campo, nombre in nombres.items():
			self.assertNotIn(
				nombre, texto,
				f"el PDF público no puede llevar el nombre de {campo}: es dato personal (Ley 29733)",
			)
		self.assertIn("Versión", texto, "en su lugar debe constar el acto: versión, fecha, estado")

	def test_no_promete_un_fichero_que_no_esta(self):
		"""El registro `File` y el fichero son dos cosas distintas y se separan.

		Si `pdf_publicado()` devolviera la ruta de un registro huérfano, quien la
		consuma haría `open()` y petaría —o serviría un 500 en una web pública—.
		Ante un registro sin fichero se responde «no hay», igual que sin registro.
		"""
		import os

		ficha = self._ficha_publicada()
		ficha.estado = "Publicado"
		ficha.save(ignore_permissions=True)
		self.assertIsNotNone(ficha_pdf.pdf_publicado(ficha.name))

		# Se borra el FICHERO dejando el registro: el caso que el contrato no cubría.
		nombre = frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Ficha Caracterizacion Proceso", "attached_to_name": ficha.name},
			pluck="name",
		)[0]
		ruta = frappe.get_doc("File", nombre).get_full_path()
		os.remove(ruta)

		self.assertIsNone(
			ficha_pdf.pdf_publicado(ficha.name),
			"con el registro presente pero el fichero ausente, no se puede prometer el PDF",
		)
