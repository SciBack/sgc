# Copyright (c) 2026, SciBack and Contributors
# See license.txt

import unittest

from sgc.sgc_procesos.doctype.proceso.proceso_tree import (
	BpmnInvalido,
	extraer_tareas_bpmn,
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
