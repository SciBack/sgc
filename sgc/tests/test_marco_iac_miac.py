# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Marco «Ejes Temáticos de Autoevaluación del IAC (MIAC)» y su preparación de evidencias.

Carga el YAML real del producto (Tabla 2 del instructivo, RS 00105-2026-SUNEDU) dentro de un
savepoint que se deshace, y comprueba lo que el MIAC necesita: cuatro niveles (marco → eje → subeje
→ pantalla o formato), 48 pantallas y 12 formatos, sin escala de valoración, y que el informe y la
carga por ZIP trabajen sobre las pantallas.
"""

import contextlib
import io
import os

import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f2_load_coneau, marcos_normativos
from sgc.sgc_acreditacion.doctype.carga_evidencias.carga_evidencias import CargaEvidencias
from sgc.sgc_acreditacion.report.preparacion_de_evidencias import preparacion_de_evidencias as informe
from sgc.tests import factories

MARCO = "SUNEDU-IAC-MIAC-2026"
SAVEPOINT = "marco_iac"


class IntegrationTestMarcoIAC(IntegrationTestCase):
	def setUp(self):
		frappe.db.savepoint(SAVEPOINT)
		self.addCleanup(frappe.db.rollback, save_point=SAVEPOINT)
		with contextlib.redirect_stdout(io.StringIO()):
			f2_load_coneau.run(marcos_normativos.resolver("sunedu-iac-miac-2026"), commit=False)

	def test_cuatro_niveles_con_48_pantallas_y_12_formatos(self):
		elementos = frappe.get_all("Elemento Marco", filters={"marco_normativo": MARCO},
								   fields=["name", "tipo", "is_group", "denominacion"])
		self.assertEqual(len(elementos), 1 + 8 + 21 + 60)
		hojas = [e for e in elementos if not e.is_group]
		self.assertEqual(len(hojas), 60)
		self.assertEqual(sum(e.denominacion.startswith("[P]") for e in hojas), 48)
		self.assertEqual(sum(e.denominacion.startswith("[F]") for e in hojas), 12)
		self.assertEqual(frappe.db.get_value("Elemento Marco", "IAC-1", ["tipo", "is_group"]), ("Factor", 1))
		self.assertEqual(frappe.db.get_value("Elemento Marco", "IAC-1.1", ["tipo", "is_group"]), ("Componente", 1))
		self.assertEqual(frappe.db.get_value("Elemento Marco", "IAC-1.1.1", ["tipo", "is_group", "parent_elemento_marco"]),
						 ("Criterio", 0, "IAC-1.1"))

	def test_el_marco_no_se_valora_y_es_de_licenciamiento(self):
		marco = frappe.db.get_value("Marco Normativo", MARCO, ["ente", "alcance", "escala_valoracion"], as_dict=True)
		self.assertEqual((marco.ente, marco.alcance), ("SUNEDU", "Licenciamiento"))
		self.assertFalse(marco.escala_valoracion)
		self.assertFalse(frappe.db.exists("Escala Valoracion", f"{MARCO}-ESCALA"))

	def test_los_formatos_del_siu_lo_advierten(self):
		texto = frappe.db.get_value("Elemento Marco", {"marco_normativo": MARCO, "denominacion": "[F] Relación de programas"},
									"texto_oficial")
		self.assertIn("SIU", texto)

	def test_el_informe_muestra_responsable_y_avance(self):
		unidad = frappe.get_all("Unidad Organica", pluck="name", limit=1)
		if unidad:
			frappe.db.set_value("Elemento Marco", "IAC-1.1.1", "unidad_responsable", unidad[0])
		ev = factories.crear_evidencia(prefijo="TIAC")
		factories.crear_trazabilidad(ev.name, elemento_marco="IAC-1.1.1")

		_c, data, _m, grafico, resumen = informe.execute({"marco_normativo": MARCO})
		self.assertEqual(len(data), 60)
		fila = next(f for f in data if f["elemento"] == "IAC-1.1.1")
		self.assertEqual((fila["evidencias"], fila["validas"], fila["estado"]), (1, 0, informe.POR_VALIDAR))
		self.assertTrue(fila["eje"].startswith("1. Gestión institucional"))
		self.assertEqual(resumen[1]["value"], 1)
		self.assertEqual(len(grafico["data"]["labels"]), 8)
		if unidad:
			_c, solo, *_ = informe.execute({"marco_normativo": MARCO, "unidad_responsable": unidad[0]})
			self.assertEqual([f["elemento"] for f in solo], ["IAC-1.1.1"])

	def test_la_carga_por_zip_reconoce_la_carpeta_de_la_pantalla(self):
		carga = frappe.get_doc({"doctype": "Carga Evidencias", "marco_normativo": MARCO})
		claves = CargaEvidencias._elementos(carga)
		elemento, _t = CargaEvidencias._resolver(carga, "IAC/1. Gestión/1.1.1 Modelo educativo/modelo.pdf", {}, claves)
		self.assertEqual(elemento, "IAC-1.1.1")
		elemento, _t = CargaEvidencias._resolver(carga, "IAC/4.4.1 Plan de mantenimiento/plan.pdf", {}, claves)
		self.assertEqual(frappe.db.get_value("Elemento Marco", elemento, "denominacion"),
						 "[P] Plan de mantenimiento de infraestructura, equipamiento y mobiliario")
