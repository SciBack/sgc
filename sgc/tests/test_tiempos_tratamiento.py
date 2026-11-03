# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests del informe «Tiempos de tratamiento».

Cubre los tramos de estado reconstruidos del historial (`Version`), los días por estado y
hasta el cierre con fechas fijadas en el pasado, que el tramo de un estado final no cuenta,
que quien no lee el tipo de registro no ve nada, y que cada tipo medido tiene de verdad sus
estados de cierre.
"""

import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_datetime, now_datetime

from sgc.sgc_nucleo.report.tiempos_de_tratamiento import tiempos_de_tratamiento as informe
from sgc.tests import factories

NC = "No Conformidad"


class TestTramos(IntegrationTestCase):
	def test_sin_cambios_es_un_solo_tramo_en_curso(self):
		t = informe.tramos("2026-01-01 00:00:00", "Abierta", [], "2026-01-05 00:00:00")
		self.assertEqual([(e, en_curso) for e, _i, _f, en_curso in t], [("Abierta", True)])
		self.assertEqual(informe.dias(t[0][1], t[0][2]), 4)

	def test_cada_cambio_cierra_un_tramo(self):
		cambios = [("2026-01-03 00:00:00", "Abierta", "En analisis"),
				   ("2026-01-04 12:00:00", "En analisis", "En tratamiento")]
		t = informe.tramos("2026-01-01 00:00:00", "En tratamiento", cambios, "2026-01-10 00:00:00")
		self.assertEqual([e for e, *_ in t], ["Abierta", "En analisis", "En tratamiento"])
		self.assertEqual([round(informe.dias(i, f), 1) for _e, i, f, _c in t], [2, 1.5, 5.5])
		self.assertEqual([c for *_, c in t], [False, False, True])


class IntegrationTestTiemposTratamiento(IntegrationTestCase):
	def setUp(self):
		factories.desactivar_workflow(NC)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.db.delete(NC)

	def _nc(self, hace_dias):
		nc = frappe.get_doc({"doctype": NC, "titulo": "NC de prueba de tiempos", "tipo": "No conformidad menor",
							 "estado": "Abierta"}).insert(ignore_permissions=True)
		frappe.db.set_value(NC, nc.name, "creation", add_days(now_datetime(), -hace_dias), update_modified=False)
		return nc.name

	def _cambio(self, nombre, anterior, nuevo, hace_dias):
		v = frappe.get_doc({"doctype": "Version", "ref_doctype": NC, "docname": nombre,
							"data": json.dumps({"changed": [["estado", anterior, nuevo]]})}).insert(ignore_permissions=True)
		frappe.db.set_value("Version", v.name, "creation", add_days(now_datetime(), -hace_dias), update_modified=False)
		frappe.db.set_value(NC, nombre, "estado", nuevo, update_modified=False)

	def _filas(self, **filtros):
		_cols, data, _msg, grafico, resumen = informe.execute({"tipo": NC, **filtros})
		return {f["estado"]: f for f in data}, grafico, {r["label"]: r["value"] for r in resumen}

	def test_dias_por_estado_y_hasta_el_cierre(self):
		abierta = self._nc(10)
		self._cambio(abierta, "Abierta", "En analisis", 6)       # 4 días abierta, 6 en análisis (en curso)
		cerrada = self._nc(20)
		self._cambio(cerrada, "Abierta", "Cerrada eficaz", 12)   # 8 días abierta y cerrada

		filas, grafico, resumen = self._filas()
		self.assertEqual(filas["Abierta"]["pasaron"], 2)
		self.assertAlmostEqual(filas["Abierta"]["dias_promedio"], 6.0, delta=0.1)
		self.assertEqual(filas["En analisis"]["en_curso"], 1)
		self.assertAlmostEqual(filas["En analisis"]["dias_en_curso"], 6.0, delta=0.1)
		self.assertNotIn("Cerrada eficaz", filas)  # un estado final no es espera
		self.assertEqual((resumen["Registros"], resumen["Cerrados"]), (2, 1))
		self.assertAlmostEqual(resumen["Días promedio hasta el cierre"], 8.0, delta=0.1)
		self.assertEqual(grafico["type"], "bar")

	def test_sin_registros_no_falla(self):
		filas, grafico, resumen = self._filas()
		self.assertEqual((filas, grafico, resumen["Registros"]), ({}, None, 0))

	def test_el_filtro_de_fechas_acota_por_creacion(self):
		self._nc(40)
		self._nc(2)
		_filas, _g, resumen = self._filas(desde=add_days(now_datetime(), -5).date())
		self.assertEqual(resumen["Registros"], 1)

	def test_quien_no_lee_el_tipo_no_ve_nada(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			informe.execute({"tipo": NC})

	def test_un_tipo_no_medido_se_rechaza(self):
		with self.assertRaises(frappe.ValidationError):
			informe.execute({"tipo": "User"})

	def test_cada_tipo_medido_tiene_sus_estados_de_cierre(self):
		for tipo, cierres in informe.CIERRES.items():
			with self.subTest(tipo=tipo):
				meta = frappe.get_meta(tipo)
				self.assertTrue(meta.track_changes, f"{tipo} sin track_changes: no habría historial")
				opciones = set((meta.get_field("estado").options or "").split("\n"))
				self.assertEqual(set(cierres) - opciones, set())
				self.assertEqual(set(informe.OTROS_FINALES.get(tipo, ())) - opciones, set())

	def test_el_tramo_empieza_al_crearse(self):
		nombre = self._nc(3)
		filas, _g, _r = self._filas()
		self.assertAlmostEqual(filas["Abierta"]["dias_en_curso"], 3.0, delta=0.1)
		self.assertEqual(get_datetime(frappe.db.get_value(NC, nombre, "creation")).date(),
						 add_days(now_datetime(), -3).date())
