# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Carga masiva de evidencias desde un ZIP (M09, criterio del MVP «500 evidencias cargadas»).

Se arma un ZIP en memoria con la forma en que las facultades guardan hoy las evidencias
(carpetas por estándar y criterio), se adjunta y se valida la carga: debe crear una
Evidencia por archivo, vincularla al criterio que dice su carpeta o el `indice.csv`, y
omitir lo que no es evidencia (basura del sistema, tipos raros, rutas con «..», repetidos).
"""

import io
import zipfile

import frappe
from frappe.tests import IntegrationTestCase

from sgc.tests import factories

P = "TCE"


def _zip(archivos):
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, "w") as zf:
		for ruta, contenido in archivos.items():
			zf.writestr(ruta, contenido)
	return buffer.getvalue()


class IntegrationTestCargaEvidencias(IntegrationTestCase):
	def setUp(self):
		marco = factories._ensure_named("Marco Normativo", f"{P}-MARCO", {
			"nombre": "Marco de prueba de carga", "ente": "SINEACE", "version": "1", "estado": "vigente",
		})
		self.marco = marco.name
		self.el = {}
		for est, crits in (("E1", ("1.1", "1.2")), ("E2", ("2.1",))):
			e = factories._ensure_named("Elemento Marco", f"{P}-{est}", {
				"denominacion": f"Estándar {est}", "marco_normativo": self.marco, "nivel": "2", "tipo": "Estandar",
				"is_group": 1,
			})
			self.el[est] = e.name
			for c in crits:
				self.el[c] = factories._ensure_named("Elemento Marco", f"{P}-{c}", {
					"denominacion": f"Criterio {c}", "marco_normativo": self.marco, "nivel": "3", "tipo": "Criterio",
					"es_valorable": 1, "parent_elemento_marco": e.name,
				}).name

	def _cargar(self, archivos, **extra):
		adjunto = frappe.get_doc({"doctype": "File", "file_name": f"evidencias-{frappe.generate_hash(length=6)}.zip",
								  "content": _zip(archivos), "is_private": 1}).insert(ignore_permissions=True)
		carga = frappe.get_doc({"doctype": "Carga Evidencias", "archivo_zip": adjunto.file_url,
								"marco_normativo": self.marco, **extra}).insert(ignore_permissions=True)
		carga.submit()
		return frappe.get_doc("Carga Evidencias", carga.name)

	def _fila(self, carga, archivo):
		return next(f for f in carga.filas if f.archivo == archivo)

	def test_carpetas_por_estandar_y_criterio(self):
		carga = self._cargar({
			"Evidencias/Estándar 1/1.1 Propósitos/acta-aprobacion.pdf": b"acta 1.1",
			"Evidencias/E1/Criterio 1.2/plan_operativo.docx": b"plan 1.2",
			"Evidencias/Estándar 2/informe.xlsx": b"informe del estandar 2",
			"Evidencias/otros/suelto.pdf": b"sin criterio",
			"Evidencias/Criterio 1.2/1. Inventario/inventario.xlsx": b"inventario numerado",
			"Evidencias/2. Carpeta numerada/z.pdf": b"numerada sin criterio",
			"__MACOSX/Evidencias/._acta.pdf": b"basura",
			"Evidencias/.DS_Store": b"basura",
			"Evidencias/instalador.exe": b"no es evidencia",
		})
		self.assertEqual(self._fila(carga, "Evidencias/Estándar 1/1.1 Propósitos/acta-aprobacion.pdf").elemento_marco, self.el["1.1"])
		self.assertEqual(self._fila(carga, "Evidencias/E1/Criterio 1.2/plan_operativo.docx").elemento_marco, self.el["1.2"])
		self.assertEqual(self._fila(carga, "Evidencias/Estándar 2/informe.xlsx").elemento_marco, self.el["E2"])
		self.assertFalse(self._fila(carga, "Evidencias/otros/suelto.pdf").elemento_marco)
		# Una carpeta numerada no es el Estándar 1 ni el 2: manda la carpeta de criterio de encima.
		self.assertEqual(self._fila(carga, "Evidencias/Criterio 1.2/1. Inventario/inventario.xlsx").elemento_marco, self.el["1.2"])
		self.assertFalse(self._fila(carga, "Evidencias/2. Carpeta numerada/z.pdf").elemento_marco)
		self.assertIn("tipo no admitido", self._fila(carga, "Evidencias/instalador.exe").resultado)
		self.assertEqual(len(carga.filas), 7)  # la basura del sistema ni siquiera se lista
		self.assertEqual((carga.n_creadas, carga.n_vinculadas, carga.n_sin_vinculo, carga.n_omitidos), (6, 4, 2, 1))
		self.assertEqual(carga.estado, "Con observaciones")

		ev = frappe.get_doc("Evidencia", self._fila(carga, "Evidencias/E1/Criterio 1.2/plan_operativo.docx").evidencia)
		self.assertEqual(ev.titulo, "plan operativo")
		self.assertTrue(ev.archivo.startswith("/private/files/"))
		self.assertTrue(ev.hash_sha256)
		self.assertEqual((ev.origen_doctype, ev.origen_id), ("Carga Evidencias", carga.name))
		self.assertEqual(frappe.db.get_value("File", {"file_url": ev.archivo, "attached_to_name": ev.name}, "attached_to_doctype"), "Evidencia")
		self.assertTrue(frappe.db.exists("Trazabilidad", {"evidencia": ev.name, "elemento_marco": self.el["1.2"]}))
		self.assertEqual(frappe.get_doc("Evidencia", self._fila(carga, "Evidencias/Estándar 2/informe.xlsx").evidencia).tipo, "Dataset")

	def test_indice_csv_manda_sobre_las_carpetas(self):
		indice = f"archivo,elemento,titulo\nencuesta.pdf,2.1,Encuesta de satisfacción 2026\nsub/acta.pdf,{P}-1.1,\n"
		carga = self._cargar({
			"indice.csv": indice.encode(),
			"Estándar 1/encuesta.pdf": b"encuesta",
			"sub/acta.pdf": b"acta",
		})
		fila = self._fila(carga, "Estándar 1/encuesta.pdf")
		self.assertEqual(fila.elemento_marco, self.el["2.1"])
		self.assertEqual(frappe.db.get_value("Evidencia", fila.evidencia, "titulo"), "Encuesta de satisfacción 2026")
		self.assertEqual(self._fila(carga, "sub/acta.pdf").elemento_marco, self.el["1.1"])
		self.assertEqual(carga.estado, "Procesada")

	def test_repetidos_y_rutas_peligrosas_se_omiten(self):
		self._cargar({"1.1/acta.pdf": b"contenido unico de prueba de repetidos"})
		carga = self._cargar({
			"copia/1.1/acta-copia.pdf": b"contenido unico de prueba de repetidos",  # ya cargado
			"1.2/a.pdf": b"dos veces en el mismo zip",
			"1.2/b.pdf": b"dos veces en el mismo zip",
			"../fuera.pdf": b"zip slip",
		})
		self.assertIn("ya cargado", self._fila(carga, "copia/1.1/acta-copia.pdf").resultado)
		self.assertIn("ya cargado", self._fila(carga, "1.2/b.pdf").resultado)
		self.assertIn("ruta no permitida", self._fila(carga, "../fuera.pdf").resultado)
		self.assertEqual((carga.n_creadas, carga.n_omitidos), (1, 3))

	def test_proceso_vincula_lo_que_no_tiene_criterio(self):
		proceso = factories.crear_proceso()
		carga = self._cargar({"varios/foto.jpg": b"foto del proceso"}, proceso=proceso.name)
		fila = self._fila(carga, "varios/foto.jpg")
		self.assertTrue(frappe.db.exists("Trazabilidad", {"evidencia": fila.evidencia, "proceso": proceso.name}))
		self.assertEqual(carga.n_sin_vinculo, 0)

	def test_no_es_un_zip(self):
		adjunto = frappe.get_doc({"doctype": "File", "file_name": "falso.zip", "content": b"no soy un zip",
								  "is_private": 1}).insert(ignore_permissions=True)
		carga = frappe.get_doc({"doctype": "Carga Evidencias", "archivo_zip": adjunto.file_url,
								"marco_normativo": self.marco}).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			carga.submit()

	def test_solo_zip(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "Carga Evidencias", "archivo_zip": "/private/files/x.pdf",
							"marco_normativo": self.marco}).insert(ignore_permissions=True)
