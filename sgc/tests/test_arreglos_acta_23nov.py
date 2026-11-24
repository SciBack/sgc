"""Arreglos de la demo con la DPGC del 23-nov-2026 (SGC 1.7.24).

1. La no conformidad se registra con el formulario completo (sin alta rápida): por la ventana corta
   se guardaba sin «Requiere análisis de causa».
2. En «Abierta» la corrigen quien la registra en la DPGC (DPGC y Analista), no solo el Responsable de
   Calidad de Programa; y una NC «Abierta» se puede borrar. Desde «En analisis», no.
3. El código de la acción de mejora (y de los otros seis DocTypes que lo generan) ya no es obligatorio
   en el formulario: si se deja vacío, lo pone el sistema.
4. La acción creada desde una NC toma el responsable de la NC si no se indica otro.
5. Los usuarios se ven por su nombre en los campos que enlazan con un usuario.

Hereda de `IntegrationTestCase`: cada test corre en su transacción con rollback.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc import estandar

CON_CODIGO_AUTOMATICO = (
	"Accion Mejora", "Plan Mejora", "Hallazgo", "Evidencia",
	"Programa Auditoria", "Hallazgo Auditoria", "Informe Auditoria",
)


def _nc(**extra):
	return frappe.get_doc({"doctype": "No Conformidad", "titulo": "NC de prueba 1.7.24", **extra}).insert(
		ignore_permissions=True)


class IntegrationTestArreglosActa23Nov(IntegrationTestCase):
	def test_la_nc_se_registra_con_el_formulario_completo(self):
		self.assertFalse(frappe.get_meta("No Conformidad").quick_entry)

	def test_en_abierta_editan_dpgc_y_analista_y_despues_solo_el_rcp(self):
		wf = estandar.workflow_de("No Conformidad")
		por_estado = {}
		for s in wf["states"]:
			por_estado.setdefault(s["state"], set()).add(s["allow_edit"])
		self.assertEqual(por_estado["Abierta"], {
			"Responsable de Calidad de Programa", "DPGC", "Analista de Calidad (DPGC)"})
		self.assertEqual(por_estado["En analisis"], {"Responsable de Calidad de Programa"})

	def test_dpgc_y_analista_pueden_borrar_una_nc(self):
		meta = frappe.get_meta("No Conformidad")
		borran = {p.role for p in meta.permissions if p.delete}
		self.assertEqual(borran, {"DPGC", "Analista de Calidad (DPGC)"})

	def test_una_nc_abierta_se_borra(self):
		nc = _nc()
		frappe.delete_doc("No Conformidad", nc.name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("No Conformidad", nc.name))

	def test_una_nc_en_analisis_no_se_borra(self):
		nc = _nc(responsable="Administrator")
		frappe.db.set_value("No Conformidad", nc.name, "estado", "En analisis")
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("No Conformidad", nc.name, ignore_permissions=True)
		self.assertTrue(frappe.db.exists("No Conformidad", nc.name))

	def test_el_codigo_no_es_obligatorio_donde_lo_pone_el_sistema(self):
		for doctype in CON_CODIGO_AUTOMATICO:
			with self.subTest(doctype=doctype):
				self.assertFalse(frappe.get_meta(doctype).get_field("codigo").reqd)

	def test_la_accion_sin_codigo_lo_recibe_y_hereda_el_responsable_de_la_nc(self):
		nc = _nc(responsable="Administrator")
		accion = frappe.get_doc({"doctype": "Accion Mejora", "no_conformidad": nc.name}).insert(
			ignore_permissions=True)
		self.assertTrue(accion.codigo.startswith("AM-"))
		self.assertEqual(accion.name, accion.codigo)
		self.assertEqual(accion.responsable, "Administrator")

	def test_la_accion_respeta_el_responsable_que_se_indica(self):
		nc = _nc(responsable="Administrator")
		accion = frappe.get_doc({"doctype": "Accion Mejora", "no_conformidad": nc.name,
								 "responsable": "Guest"}).insert(ignore_permissions=True)
		self.assertEqual(accion.responsable, "Guest")

	def test_los_usuarios_se_ven_por_su_nombre(self):
		self.assertTrue(frappe.get_meta("User").show_title_field_in_link)
