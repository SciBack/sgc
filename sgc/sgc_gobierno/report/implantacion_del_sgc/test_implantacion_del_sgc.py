# Copyright (c) 2026, SciBack and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from sgc.sgc_gobierno.report.implantacion_del_sgc import implantacion_del_sgc as informe


class IntegrationTestImplantacionDelSgc(IntegrationTestCase):
	def test_mide_los_nueve_criterios(self):
		columnas, data, _mensaje, grafico, resumen = informe.execute()
		self.assertEqual(len(data), 9)
		self.assertEqual(len(grafico["data"]["datasets"][0]["values"]), 9)
		for fila in data:
			self.assertTrue(0 <= fila["avance"] <= 100)
			self.assertIn(fila["estado"], informe.ESTADOS)
			if fila["estado"] != "Cumple":
				self.assertTrue(fila["falta"], fila["criterio"])
		self.assertIn("/", resumen[0]["value"])

	def test_estado_segun_meta(self):
		self.assertEqual(informe.fila("x", 50, 50, "f")["estado"], "Cumple")
		self.assertEqual(informe.fila("x", 50, 49, "f")["estado"], "En curso")
		self.assertEqual(informe.fila("x", 50, 0, "f")["estado"], "Sin empezar")
		self.assertEqual(informe.fila("x", 50, 0, "f")["falta"], "f")
		self.assertEqual(informe.fila("x", 50, 60, "f")["avance"], 100)

	def test_la_instancia_ajusta_las_metas(self):
		frappe.conf["sgc_metas_implantacion"] = {"documentos": 7}
		try:
			self.assertEqual(informe.metas()["documentos"], 7)
			self.assertEqual(informe.metas()["evidencias"], 500)
		finally:
			frappe.conf.pop("sgc_metas_implantacion", None)
