"""El módulo con nombre de cliente se retira solo si nada lo usa."""

import frappe
from frappe.tests import IntegrationTestCase

from sgc.patches import retirar_modulo_del_cliente as parche

MODULO = parche.MODULO


class IntegrationTestRetirarModuloDelCliente(IntegrationTestCase):
	def _crear_modulo(self):
		if not frappe.db.exists("Module Def", MODULO):
			frappe.get_doc({"doctype": "Module Def", "module_name": MODULO, "app_name": "sgc"}).insert(
				ignore_permissions=True
			)

	def test_el_canonico_no_declara_el_modulo(self):
		self.assertNotIn(MODULO, frappe.get_module_list("sgc"))

	def test_un_modulo_huerfano_se_retira(self):
		self._crear_modulo()
		parche.execute()
		self.assertFalse(frappe.db.exists("Module Def", MODULO))

	def test_un_modulo_en_uso_se_conserva(self):
		self._crear_modulo()
		# IntegrationTestCase no deshace cada test: sin limpiar, este informe hace
		# que el test del módulo huérfano vea el módulo «en uso».
		informe = frappe.get_doc({
			"doctype": "Report",
			"report_name": "Informe del cliente de prueba",
			"ref_doctype": "Proceso",
			"report_type": "Report Builder",
			"is_standard": "No",
			"module": MODULO,
		}).insert(ignore_permissions=True)
		self.addCleanup(frappe.delete_doc, "Report", informe.name, force=True, ignore_permissions=True)
		parche.execute()
		self.assertTrue(frappe.db.exists("Module Def", MODULO))

	def test_sin_modulo_el_parche_no_hace_nada(self):
		frappe.db.delete("Module Def", {"name": MODULO})
		parche.execute()
		self.assertFalse(frappe.db.exists("Module Def", MODULO))
