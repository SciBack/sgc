# Copyright (c) 2026, SciBack and Contributors
# See license.txt

import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from types import SimpleNamespace
from typing import ClassVar

from sgc.sgc_procesos.doctype.proceso import proceso_tree
from sgc.sgc_procesos.doctype.proceso.proceso_tree import (
	BpmnInvalido,
	extraer_tareas_bpmn,
)

try:
	import frappe
	from frappe.permissions import add_permission, update_permission_property
	from frappe.tests import IntegrationTestCase
except ModuleNotFoundError:  # permite ejecutar localmente las pruebas puras del parser
	frappe = None
	IntegrationTestCase = unittest.TestCase


class TestContratoPublicoTree(unittest.TestCase):
	def test_expone_el_proveedor_de_hijos(self):
		self.assertTrue(callable(getattr(proceso_tree, "get_children", None)))

	def test_log_bpmn_invalido_es_atomico_persistente_ante_concurrencia(self):
		class CacheFalso:
			def __init__(self):
				self.lock = Lock()
				self.values = {}
				self.logical_keys = []
				self.set_calls = []

			def make_key(self, key):
				self.logical_keys.append(key)
				return f"test-db|{key}".encode()

			def set(self, *, name, value, **kwargs):
				with self.lock:
					self.set_calls.append((name, value, kwargs))
					if kwargs.get("nx") and name in self.values:
						return None
					self.values[name] = value
					return True

		cache = CacheFalso()
		logs = []
		frappe_falso = SimpleNamespace(
			cache=cache,
			log_error=lambda **kwargs: logs.append(kwargs),
		)
		file_row = SimpleNamespace(
			name="FILE-BPMN-001",
			modified="2026-09-01 15:00:00.000000",
		)

		with ThreadPoolExecutor(max_workers=8) as executor:
			list(
				executor.map(
					lambda _: proceso_tree._log_bpmn_invalido(
						frappe_falso, file_row, BpmnInvalido("XML inválido")
					),
					range(32),
				)
			)

		self.assertEqual(len(logs), 1)
		self.assertEqual(len(cache.values), 1)
		self.assertEqual(len(cache.set_calls), 32)
		self.assertTrue(
			all(call[2] == {"nx": True} for call in cache.set_calls),
			"SET NX no debe incluir expiración",
		)
		self.assertTrue(
			all(
				key.endswith("FILE-BPMN-001:2026-09-01 15:00:00.000000")
				for key in cache.logical_keys
			)
		)


@unittest.skipIf(frappe is None, "requiere un sitio Frappe de pruebas")
class IntegrationTestProcesoTree(IntegrationTestCase):
	CAMPOS_NODO: ClassVar[set[str]] = {
		"value",
		"title",
		"expandable",
		"node_type",
		"doctype",
		"docname",
		"file_name",
		"bpmn_id",
	}

	def setUp(self):
		super().setUp()
		self.usuario_anterior = frappe.session.user
		frappe.set_user("Administrator")
		sufijo = frappe.generate_hash(length=8).upper()
		self.prefijo = f"TEST-TREE-{sufijo}"
		self.raiz = self._crear_proceso(f"{self.prefijo}-N0", None, 1)
		self.proceso = self._crear_proceso(f"{self.prefijo}-N1", self.raiz, 1)
		self.subproceso = self._crear_proceso(f"{self.prefijo}-N2", self.proceso, 0)
		self.procedimiento = frappe.get_doc(
			{
				"doctype": "Procedimiento",
				"codigo": f"{self.prefijo}-PR-001",
				"titulo": "Procedimiento real <seguro>",
				"proceso": self.subproceso,
			}
		).insert(ignore_permissions=True)
		self.bpmn = self._crear_archivo(
			"flujo-real.bpmn",
			"""<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
			  <bpmn:process id="Process_1">
			    <bpmn:userTask id="Task_1" name="Revisar &lt;solicitud&gt;" />
			    <bpmn:serviceTask id="Task_2" />
			  </bpmn:process>
			</bpmn:definitions>""",
			self.procedimiento.name,
		)
		self._asociar_diagrama(self.bpmn.file_url)

		self.rol_proceso = f"{self.prefijo}-PROCESO"
		self.rol_completo = f"{self.prefijo}-COMPLETO"
		self.usuario_solo_proceso = self._crear_usuario(
			"solo-proceso", self.rol_proceso, ("Proceso",)
		)
		self.usuario_completo = self._crear_usuario(
			"completo", self.rol_completo, ("Proceso", "Procedimiento")
		)

	def tearDown(self):
		frappe.set_user(self.usuario_anterior)
		super().tearDown()

	def _crear_proceso(self, codigo, parent, is_group):
		return frappe.get_doc(
			{
				"doctype": "Proceso",
				"codigo": codigo,
				"proceso": f"Denominación {codigo}",
				"nivel": "Soporte",
				"parent_proceso": parent,
				"is_group": is_group,
			}
		).insert(ignore_permissions=True).name

	def _crear_archivo(self, nombre, content, attached_to_name):
		return frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{self.prefijo}-{nombre}",
				"is_private": 1,
				"content": content,
				"attached_to_doctype": "Procedimiento",
				"attached_to_name": attached_to_name,
			}
		).insert(ignore_permissions=True)

	def _asociar_diagrama(self, file_url):
		frappe.db.set_value(
			"Procedimiento",
			self.procedimiento.name,
			"diagrama_flujo",
			file_url,
			update_modified=False,
		)

	def _crear_usuario(self, local, role, doctypes):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role,
				"desk_access": 1,
				"is_custom": 1,
			}
		).insert(ignore_permissions=True)
		for doctype in doctypes:
			add_permission(doctype, role, 0)
			update_permission_property(doctype, role, 0, "read", 1, validate=False)
		email = f"{local}-{self.prefijo.lower()}@example.test"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": local,
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=email)
		return email

	def _nodo(self, nodos, docname):
		return next(nodo for nodo in nodos if nodo["docname"] == docname)

	def _expandir_fixture(self, nodo_raiz):
		pendientes = [nodo_raiz]
		visitados = set()
		while pendientes:
			nodo = pendientes.pop()
			self.assertNotIn(nodo["value"], visitados, "el árbol no debe tener ciclos")
			visitados.add(nodo["value"])
			self.assertEqual(set(nodo), self.CAMPOS_NODO)
			if nodo["expandable"]:
				hijos = proceso_tree.get_children("Proceso", nodo["value"])
				pendientes.extend(hijos)
		return visitados

	def test_raiz_acepta_parent_omitido_y_vacio_con_payload_exacto(self):
		# Calentar metadatos/roles para que el conteo mida las consultas del
		# proveedor, no la inicialización perezosa de Frappe.
		proceso_tree.get_children("Proceso")
		with self.assertQueryCount(6):
			sin_parent = proceso_tree.get_children("Proceso")
		con_parent_vacio = proceso_tree.get_children("Proceso", parent="")

		self.assertEqual(sin_parent, con_parent_vacio)
		nodo = self._nodo(sin_parent, self.raiz)
		self.assertEqual(set(nodo), self.CAMPOS_NODO)
		self.assertEqual(nodo["value"], f"proceso:{self.raiz}")
		self.assertEqual(nodo["node_type"], "N0")
		self.assertEqual(nodo["doctype"], "Proceso")
		self.assertTrue(nodo["expandable"])

	def test_compone_proceso_subproceso_procedimiento_y_tareas_tipadas(self):
		hijos_raiz = proceso_tree.get_children("Proceso", f"proceso:{self.raiz}")
		nodo_proceso = self._nodo(hijos_raiz, self.proceso)
		self.assertEqual(nodo_proceso["node_type"], "N1")

		hijos_proceso = proceso_tree.get_children("Proceso", nodo_proceso["value"])
		nodo_subproceso = self._nodo(hijos_proceso, self.subproceso)
		self.assertEqual(nodo_subproceso["node_type"], "N2")

		hijos_subproceso = proceso_tree.get_children("Proceso", nodo_subproceso["value"])
		nodo_procedimiento = self._nodo(hijos_subproceso, self.procedimiento.name)
		self.assertEqual(nodo_procedimiento["value"], f"procedimiento:{self.procedimiento.name}")
		self.assertEqual(nodo_procedimiento["node_type"], "N3")
		self.assertTrue(nodo_procedimiento["expandable"])

		tareas = proceso_tree.get_children("Proceso", nodo_procedimiento["value"])
		self.assertEqual([tarea["title"] for tarea in tareas], ["Revisar <solicitud>", "Task_2"])
		self.assertEqual([tarea["bpmn_id"] for tarea in tareas], ["Task_1", "Task_2"])
		self.assertTrue(all(tarea["value"].startswith(f"tarea:{self.bpmn.name}:") for tarea in tareas))
		self.assertTrue(all(tarea["node_type"] == "N4" for tarea in tareas))
		self.assertTrue(all(not tarea["expandable"] for tarea in tareas))
		self.assertEqual(proceso_tree.get_children("Proceso", tareas[0]["value"]), [])

	def test_expand_all_termina_sin_duplicados_desde_ambas_formas_de_raiz(self):
		nodo_omitido = self._nodo(proceso_tree.get_children("Proceso"), self.raiz)
		nodo_vacio = self._nodo(proceso_tree.get_children("Proceso", parent=""), self.raiz)

		visitados_omitido = self._expandir_fixture(nodo_omitido)
		visitados_vacio = self._expandir_fixture(nodo_vacio)

		self.assertEqual(visitados_omitido, visitados_vacio)
		self.assertEqual(len(visitados_omitido), 6)

	def test_rechaza_guest_doctype_y_tokens_forjados(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			proceso_tree.get_children("Proceso")
		frappe.set_user("Administrator")
		for doctype, parent in (
			("Procedimiento", ""),
			("Proceso", "desconocido:123"),
			("Proceso", "proceso:INEXISTENTE"),
			("Proceso", "procedimiento:INEXISTENTE"),
			("Proceso", "tarea:INEXISTENTE:Task_1"),
		):
			with self.subTest(doctype=doctype, parent=parent), self.assertRaises(
				(frappe.ValidationError, frappe.PermissionError)
			):
				proceso_tree.get_children(doctype, parent)

	def test_usuario_sin_lectura_de_procedimiento_no_descubre_su_existencia(self):
		frappe.set_user(self.usuario_solo_proceso)
		hijos_proceso = proceso_tree.get_children("Proceso", f"proceso:{self.proceso}")
		nodo_subproceso = self._nodo(hijos_proceso, self.subproceso)
		self.assertFalse(nodo_subproceso["expandable"])
		self.assertEqual(
			proceso_tree.get_children("Proceso", f"proceso:{self.subproceso}"),
			[],
		)
		with self.assertRaises(frappe.PermissionError):
			proceso_tree.get_children(
				"Proceso", f"procedimiento:{self.procedimiento.name}"
			)

	def test_usuario_con_lectura_de_ambos_doctypes_ve_bpmn_privado_adjunto(self):
		frappe.set_user(self.usuario_completo)
		procedimientos = proceso_tree.get_children(
			"Proceso", f"proceso:{self.subproceso}"
		)
		nodo = self._nodo(procedimientos, self.procedimiento.name)
		self.assertTrue(nodo["expandable"])
		tareas = proceso_tree.get_children("Proceso", nodo["value"])
		self.assertEqual([tarea["bpmn_id"] for tarea in tareas], ["Task_1", "Task_2"])

	def test_usuario_sin_lectura_de_proceso_no_obtiene_datos(self):
		usuario = f"sin-roles-{self.prefijo.lower()}@example.test"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": usuario,
				"first_name": "sin-roles",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
		frappe.set_user(usuario)
		with self.assertRaises(frappe.PermissionError):
			proceso_tree.get_children("Proceso")

	def test_bpmn_ajeno_pdf_e_invalido_no_exponen_tareas(self):
		from io import BytesIO

		from pypdf import PdfWriter

		otro = frappe.get_doc(
			{
				"doctype": "Procedimiento",
				"codigo": f"{self.prefijo}-PR-OTRO",
				"titulo": "Otro procedimiento",
				"proceso": self.subproceso,
			}
		).insert(ignore_permissions=True)
		ajeno = self._crear_archivo("ajeno.bpmn", "<definitions />", otro.name)
		contenido_pdf = BytesIO()
		writer = PdfWriter()
		writer.add_blank_page(width=72, height=72)
		writer.write(contenido_pdf)
		pdf = self._crear_archivo(
			"diagrama.pdf", contenido_pdf.getvalue(), self.procedimiento.name
		)
		invalido = self._crear_archivo(
			"invalido.bpmn", "<definitions><process></definitions>", self.procedimiento.name
		)

		for archivo in (ajeno, pdf, invalido):
			with self.subTest(archivo=archivo.name):
				self._asociar_diagrama(archivo.file_url)
				self.assertEqual(
					proceso_tree.get_children(
						"Proceso", f"procedimiento:{self.procedimiento.name}"
					),
					[],
				)


class TestExtraerTareasBpmn(unittest.TestCase):
	def test_extrae_los_ocho_tipos_en_orden_con_namespace_prefijado(self):
		xml = """<?xml version="1.0" encoding="UTF-8"?>
		<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
		  <bpmn:process id="Process_1">
		    <bpmn:task id="Task_1" name="Tarea genérica" />
		    <bpmn:userTask id="Task_2" name="Revisar" />
		    <bpmn:serviceTask id="Task_3" name="Notificar" />
		    <bpmn:manualTask id="Task_4" name="Firmar" />
		    <bpmn:scriptTask id="Task_5" name="Calcular" />
		    <bpmn:sendTask id="Task_6" name="Enviar" />
		    <bpmn:receiveTask id="Task_7" name="Recibir" />
		    <bpmn:businessRuleTask id="Task_8" name="Evaluar regla" />
		  </bpmn:process>
		</bpmn:definitions>"""

		resultado = extraer_tareas_bpmn(xml)

		self.assertEqual(
			resultado,
			[
				{"id": "Task_1", "name": "Tarea genérica", "task_type": "task"},
				{"id": "Task_2", "name": "Revisar", "task_type": "userTask"},
				{"id": "Task_3", "name": "Notificar", "task_type": "serviceTask"},
				{"id": "Task_4", "name": "Firmar", "task_type": "manualTask"},
				{"id": "Task_5", "name": "Calcular", "task_type": "scriptTask"},
				{"id": "Task_6", "name": "Enviar", "task_type": "sendTask"},
				{"id": "Task_7", "name": "Recibir", "task_type": "receiveTask"},
				{
					"id": "Task_8",
					"name": "Evaluar regla",
					"task_type": "businessRuleTask",
				},
			],
		)

	def test_acepta_namespace_default_bytes_e_ignora_elementos_que_no_son_tareas(self):
		xml = b"""<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">
		  <process id="Process_1">
		    <startEvent id="Start_1" />
		    <laneSet id="LaneSet_1"><lane id="Lane_1" /></laneSet>
		    <task id="Task_1" name="Registrar" />
		    <exclusiveGateway id="Gateway_1" />
		    <sequenceFlow id="Flow_1" sourceRef="Task_1" targetRef="Gateway_1" />
		    <endEvent id="End_1" />
		  </process>
		</definitions>"""

		self.assertEqual(
			extraer_tareas_bpmn(xml),
			[{"id": "Task_1", "name": "Registrar", "task_type": "task"}],
		)

	def test_usa_id_como_nombre_si_el_nombre_falta_o_esta_vacio(self):
		xml = """<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">
		  <process id="Process_1">
		    <userTask id="Task_sin_nombre" />
		    <manualTask id="Task_nombre_vacio" name="   " />
		  </process>
		</definitions>"""

		self.assertEqual(
			[item["name"] for item in extraer_tareas_bpmn(xml)],
			["Task_sin_nombre", "Task_nombre_vacio"],
		)

	def test_rechaza_dtd_sin_distinguir_mayusculas(self):
		xml = """<!doctype definitions SYSTEM "definitions.dtd">
		<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" />"""

		with self.assertRaises(BpmnInvalido):
			extraer_tareas_bpmn(xml)

	def test_rechaza_entity_sin_distinguir_mayusculas(self):
		xml = """<!eNtItY externa SYSTEM "file:///etc/passwd">
		<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" />"""

		with self.assertRaises(BpmnInvalido):
			extraer_tareas_bpmn(xml)

	def test_rechaza_contenido_mayor_de_cinco_mib(self):
		with self.assertRaises(BpmnInvalido):
			extraer_tareas_bpmn(b" " * (5 * 1024 * 1024 + 1))

	def test_rechaza_xml_invalido(self):
		with self.assertRaises(BpmnInvalido):
			extraer_tareas_bpmn("<definitions><process></definitions>")

	def test_rechaza_tarea_sin_id_o_con_id_vacio(self):
		for atributo_id in ("", ' id=""', ' id="   "'):
			xml = (
				'<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">'
				f'<process id="Process_1"><task{atributo_id} name="Sin ID" /></process>'
				"</definitions>"
			)
			with self.subTest(atributo_id=atributo_id), self.assertRaises(BpmnInvalido):
				extraer_tareas_bpmn(xml)

	def test_rechaza_ids_duplicados(self):
		xml = """<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">
		  <process id="Process_1">
		    <userTask id="Task_duplicada" name="Primera" />
		    <serviceTask id="Task_duplicada" name="Segunda" />
		  </process>
		</definitions>"""

		with self.assertRaises(BpmnInvalido):
			extraer_tareas_bpmn(xml)


if __name__ == "__main__":
	unittest.main()
