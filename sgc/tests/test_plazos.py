# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests del estado del plazo (`sgc/plazos.py`).

Cubre:
- El cálculo, con una fecha de hoy fija: sin plazo, en plazo, por vencer, vencido, y
  cerrado en plazo o fuera de plazo con sus días de retraso.
- Que la no conformidad sella `fecha_cierre` al cerrarse, no lo reescribe al volver a
  guardarse cerrada, y lo borra si se reabre.
- Que la tarea diaria cambia a «Vencido» lo que venció sin que nadie lo tocara, sin
  cambiar `modified`.
- Que los cuatro DocTypes tienen los campos y llaman a `plazos.aplicar`, y que sus
  estados de cierre existen de verdad en su flujo.
- La tarjeta de porcentaje: N/A sin cerrados, y la proporción correcta con cerrados.
"""

import inspect
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from sgc import dashboards, plazos
from sgc.tests import factories

ADMIN = "Administrator"
HOY = "2026-06-15"


class TestCalculoPlazo(IntegrationTestCase):
	def test_sin_fecha_de_compromiso_no_tiene_plazo(self):
		self.assertEqual(plazos.calcular(None, hoy=HOY), (plazos.SIN_PLAZO, 0))
		self.assertEqual(plazos.calcular(None, fecha_cierre=HOY), (plazos.SIN_PLAZO, 0))

	def test_abierto_con_margen_esta_en_plazo(self):
		self.assertEqual(plazos.calcular("2026-06-30", hoy=HOY), (plazos.EN_PLAZO, 0))

	def test_abierto_a_siete_dias_o_menos_esta_por_vencer(self):
		self.assertEqual(plazos.calcular("2026-06-22", hoy=HOY), (plazos.POR_VENCER, 0))
		self.assertEqual(plazos.calcular(HOY, hoy=HOY), (plazos.POR_VENCER, 0))

	def test_abierto_pasado_el_compromiso_esta_vencido_con_sus_dias(self):
		self.assertEqual(plazos.calcular("2026-06-10", hoy=HOY), (plazos.VENCIDO, 5))

	def test_cerrado_el_dia_del_compromiso_esta_en_plazo(self):
		self.assertEqual(plazos.calcular(HOY, fecha_cierre=HOY), (plazos.CERRADO_EN_PLAZO, 0))

	def test_cerrado_tarde_guarda_los_dias_de_retraso(self):
		self.assertEqual(plazos.calcular("2026-06-01", fecha_cierre=HOY), (plazos.CERRADO_FUERA, 14))


class IntegrationTestPlazoNoConformidad(IntegrationTestCase):
	def setUp(self):
		factories.desactivar_workflow("No Conformidad")
		self.evidencia = factories.crear_evidencia().name

	def _nc(self, fecha_compromiso, **extra):
		vals = {
			"doctype": "No Conformidad",
			"titulo": "NC de prueba de plazos",
			"tipo": "No conformidad menor",
			"estado": "Abierta",
			"fecha_compromiso": fecha_compromiso,
		}
		vals.update(extra)
		return frappe.get_doc(vals).insert(ignore_permissions=True)

	def _cerrar(self, nc):
		nc.update({
			"estado": "Cerrada eficaz",
			"responsable": ADMIN,
			"correccion_inmediata": "Corrección aplicada.",
			"evidencia_cierre": self.evidencia,
		})
		nc.save(ignore_permissions=True)
		return nc

	def test_abierta_calcula_su_estado_al_guardar(self):
		nc = self._nc(add_days(nowdate(), -3))
		self.assertEqual((nc.estado_plazo, nc.dias_retraso), (plazos.VENCIDO, 3))
		self.assertIsNone(nc.fecha_cierre)

	def test_sin_fecha_de_compromiso_queda_sin_plazo(self):
		nc = self._nc(None)
		self.assertEqual(nc.estado_plazo, plazos.SIN_PLAZO)

	def test_cerrar_en_plazo_sella_la_fecha_de_cierre(self):
		nc = self._cerrar(self._nc(add_days(nowdate(), 10)))
		self.assertEqual(getdate(nc.fecha_cierre), getdate(nowdate()))
		self.assertEqual((nc.estado_plazo, nc.dias_retraso), (plazos.CERRADO_EN_PLAZO, 0))

	def test_cerrar_tarde_guarda_el_retraso(self):
		nc = self._cerrar(self._nc(add_days(nowdate(), -4)))
		self.assertEqual((nc.estado_plazo, nc.dias_retraso), (plazos.CERRADO_FUERA, 4))

	def test_guardarla_otra_vez_cerrada_no_mueve_la_fecha_de_cierre(self):
		nc = self._cerrar(self._nc(add_days(nowdate(), 10)))
		anterior = add_days(nowdate(), -2)
		frappe.db.set_value("No Conformidad", nc.name, "fecha_cierre", anterior, update_modified=False)
		nc.reload()
		nc.save(ignore_permissions=True)
		self.assertEqual(getdate(nc.fecha_cierre), getdate(anterior))

	def test_reabrirla_borra_la_fecha_de_cierre(self):
		nc = self._cerrar(self._nc(add_days(nowdate(), 10)))
		nc.estado = "En verificacion"
		nc.save(ignore_permissions=True)
		self.assertIsNone(nc.fecha_cierre)
		self.assertEqual(nc.estado_plazo, plazos.EN_PLAZO)

	def test_la_tarea_diaria_marca_lo_que_vencio_sin_tocar_modified(self):
		nc = self._nc(add_days(nowdate(), 30))
		self.assertEqual(nc.estado_plazo, plazos.EN_PLAZO)
		# Pasa el tiempo sin que nadie guarde la NC.
		frappe.db.set_value("No Conformidad", nc.name, "fecha_compromiso", add_days(nowdate(), -2),
							update_modified=False)
		modificado = frappe.db.get_value("No Conformidad", nc.name, "modified")

		with patch.object(frappe.db, "commit"):  # la tarea hace commit; el test no debe
			plazos.recalcular_abiertos()

		fila = frappe.db.get_value("No Conformidad", nc.name, ["estado_plazo", "dias_retraso", "modified"],
								   as_dict=True)
		self.assertEqual((fila.estado_plazo, fila.dias_retraso), (plazos.VENCIDO, 2))
		self.assertEqual(fila.modified, modificado)

	def test_la_tarea_diaria_no_toca_lo_cerrado(self):
		nc = self._cerrar(self._nc(add_days(nowdate(), 10)))
		frappe.db.set_value("No Conformidad", nc.name, "fecha_compromiso", add_days(nowdate(), -30),
							update_modified=False)
		with patch.object(frappe.db, "commit"):
			plazos.recalcular_abiertos()
		self.assertEqual(frappe.db.get_value("No Conformidad", nc.name, "estado_plazo"), plazos.CERRADO_EN_PLAZO)

	def test_la_tarjeta_da_na_sin_cerradas_y_el_porcentaje_con_cerradas(self):
		frappe.db.delete("No Conformidad")
		self.assertEqual(dashboards.nc_cerradas_en_plazo(), {"value": None, "fieldtype": "Percent"})

		self._cerrar(self._nc(add_days(nowdate(), 10)))
		self._cerrar(self._nc(add_days(nowdate(), -1)))
		self._nc(add_days(nowdate(), -5))  # abierta: no cuenta
		self.assertEqual(dashboards.nc_cerradas_en_plazo()["value"], 50.0)


class TestDeclaracionPlazos(IntegrationTestCase):
	def test_cada_doctype_tiene_los_campos_y_llama_a_aplicar(self):
		for doctype in plazos.CIERRES:
			with self.subTest(doctype=doctype):
				meta = frappe.get_meta(doctype)
				for campo in ("fecha_compromiso", "estado_plazo", "dias_retraso", "fecha_cierre"):
					self.assertTrue(meta.has_field(campo), f"{doctype} no tiene {campo}")
					self.assertTrue(meta.get_field(campo).read_only or campo == "fecha_compromiso")
				controlador = frappe.get_doc({"doctype": doctype}).__class__
				self.assertIn("plazos.aplicar(self)", inspect.getsource(controlador.validate))

	def test_los_estados_de_cierre_existen(self):
		"""Un estado de cierre mal escrito dejaría todo «abierto» para siempre, sin error."""
		for doctype, cierres in plazos.CIERRES.items():
			with self.subTest(doctype=doctype):
				opciones = set((frappe.get_meta(doctype).get_field("estado").options or "").split("\n"))
				self.assertEqual(set(cierres) - opciones, set())

	def test_las_opciones_del_campo_son_los_estados_que_calcula(self):
		calculados = {plazos.SIN_PLAZO, plazos.EN_PLAZO, plazos.POR_VENCER, plazos.VENCIDO,
					  plazos.CERRADO_EN_PLAZO, plazos.CERRADO_FUERA}
		for doctype in plazos.CIERRES:
			with self.subTest(doctype=doctype):
				opciones = set(frappe.get_meta(doctype).get_field("estado_plazo").options.split("\n"))
				self.assertEqual(opciones, calculados)
