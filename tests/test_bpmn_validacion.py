"""Controles XML del editor BPMN, aislados de Frappe."""
import importlib
import unittest

NS = 'http://www.omg.org/spec/BPMN/20100524/MODEL'


def xml(body='', attrs=''):
    return f'<bpmn:definitions xmlns:bpmn="{NS}" {attrs}>{body}</bpmn:definitions>'


class TestValidacionBpmn(unittest.TestCase):
    def setUp(self):
        try:
            self.v = importlib.import_module('sgc.bpmn_validacion')
        except ModuleNotFoundError:
            self.fail('Falta el validador XML del editor')

    def test_empty_definitions_and_arbitrary_prefix_are_valid(self):
        for data in (xml(), f'<definitions xmlns="{NS}"/>', f'<x:definitions xmlns:x="{NS}"/>'):
            self.assertEqual(self.v.validar_bpmn(data), data.encode())

    def test_malformed_or_forged_namespace_rejected(self):
        for data in ('<definitions/>', '<definitions xmlns="urn:fake"/>', xml('<broken>'), '<!-- <bpmn:definitions --><x/>'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.v.validar_bpmn(data)

    def test_byte_limit_not_character_limit(self):
        data = xml('<bpmn:documentation>' + 'á' * 40 + '</bpmn:documentation>')
        with self.assertRaises(ValueError):
            self.v.validar_bpmn(data, max_bytes=len(data))
        with self.assertRaises(ValueError):
            self.v.validar_bpmn(xml(' ' * self.v.MAX_BYTES_BPMN))

    def test_dtd_and_entity_rejected_before_expansion(self):
        for prefix in ('<!DOCTYPE definitions [<!ENTITY x "boom">]>', '<!DOCTYPE definitions SYSTEM "file:///etc/passwd">', '<!ENTITY x SYSTEM "https://example.test">'):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                self.v.validar_bpmn(prefix + xml())
        with self.assertRaises(ValueError):
            self.v.validar_bpmn(('<?xml version="1.0" encoding="UTF-16"?>' + xml()).encode('utf-16'))

    def test_internal_references_and_diagram_references(self):
        body = '<bpmn:process id="P"><bpmn:task id="A"><bpmn:outgoing>F</bpmn:outgoing></bpmn:task><bpmn:task id="B"/><bpmn:sequenceFlow id="F" sourceRef="A" targetRef="B"/></bpmn:process>'
        self.v.validar_bpmn(xml(body))
        for invalid in (body.replace('targetRef="B"', 'targetRef="Missing"'), body.replace('>F<', '>Missing<'), body.replace('id="B"', 'id="A"')):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.v.validar_bpmn(xml(invalid))
        diagram = '<di:BPMNDiagram xmlns:di="http://www.omg.org/spec/BPMN/20100524/DI"><di:BPMNPlane bpmnElement="Missing"/></di:BPMNDiagram>'
        with self.assertRaises(ValueError):
            self.v.validar_bpmn(xml(body + diagram))

    def test_executable_content_rejected(self):
        for body in ('<bpmn:process isExecutable="true"/>', '<bpmn:process isExecutable="1"/>', '<bpmn:scriptTask/>', '<bpmn:script>run()</bpmn:script>', '<bpmn:extensionElements/>', '<script xmlns="http://www.w3.org/1999/xhtml">x</script>', '<bpmn:task onclick="run()"/>', '<bpmn:serviceTask implementation="javascript:run()"/>'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.v.validar_bpmn(xml(body))
        self.v.validar_bpmn(xml('<bpmn:process isExecutable="false"><bpmn:serviceTask/></bpmn:process>'))

    def test_standard_namespaces_and_text_are_not_executable(self):
        data = xml('<bpmn:process id="P" name="scriptTask onclick javascript: ejemplo"><bpmn:task id="A" name="&lt;script&gt;texto&lt;/script&gt;"/></bpmn:process><bd:BPMNDiagram id="D"><bd:BPMNPlane id="Plane" bpmnElement="P"><bd:BPMNShape id="Shape" bpmnElement="A"><dc:Bounds x="0" y="0" width="100" height="80"/></bd:BPMNShape></bd:BPMNPlane></bd:BPMNDiagram>', attrs='xmlns:bd="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://example.test/bpmn schema.xsd"')
        self.v.validar_bpmn(data)

    def test_processing_instructions_are_not_saved(self):
        with self.assertRaises(ValueError):
            self.v.validar_bpmn('<?xml-stylesheet type="text/xsl" href="https://example.test/code.xsl"?>' + xml())

    def test_generated_sgc_is_readonly(self):
        for data in (xml(attrs='exporter="SGC"'), xml('<bpmn:extensionElements><s:transicion xmlns:s="https://sciback.com/sgc"/></bpmn:extensionElements>')):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.v.validar_bpmn(data)

class TestGuardadoProtegido(unittest.TestCase):
    def setUp(self):
        import importlib.util
        import sys
        import types
        from pathlib import Path
        from unittest.mock import Mock, patch

        self.mock = Mock
        self.frappe = types.ModuleType('frappe')
        self.frappe._ = lambda s: s
        self.frappe.whitelist = lambda: lambda f: f
        self.frappe.has_permission = Mock(return_value=True)
        self.frappe.throw = Mock(side_effect=ValueError('rechazado'))
        self.frappe.get_all = Mock()
        self.frappe.get_doc = Mock()
        self.frappe.delete_doc = Mock()
        self.frappe.db = Mock()
        utils = types.ModuleType('frappe.utils')
        utils.get_datetime = Mock()
        spec = importlib.util.spec_from_file_location('editor_aislado', Path(__file__).resolve().parents[1] / 'sgc/bpmn_editor.py')
        self.editor = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': self.frappe, 'frappe.utils': utils}):
            spec.loader.exec_module(self.editor)

    def test_generated_existing_cannot_be_replaced_with_unmarked_xml(self):
        import types
        self.frappe.get_all.return_value = [types.SimpleNamespace(name='A', file_name='manual.bpmn'), types.SimpleNamespace(name='B', file_name='manuala1b2c3.bpmn')]
        normal = self.mock(file_url='/private/files/manual.bpmn', file_name='manual.bpmn')
        normal.get_content.return_value = xml()
        generated = self.mock(file_url='/private/files/manuala1b2c3.bpmn', file_name='manuala1b2c3.bpmn')
        generated.get_content.return_value = xml(attrs='exporter="SGC"')
        self.frappe.get_doc.side_effect = [normal, generated]
        with self.assertRaises(ValueError):
            self.editor.guardar_bpmn('Proceso', 'P1', 'manual.bpmn', xml())
        normal.save_file.assert_not_called()
        self.frappe.delete_doc.assert_not_called()
        self.frappe.db.commit.assert_not_called()

    def test_remote_existing_is_not_downloaded(self):
        import types
        self.frappe.get_all.return_value = [types.SimpleNamespace(name='A', file_name='manual.bpmn')]
        remote = self.mock(file_url='https://example.test/private.bpmn', file_name='manual.bpmn')
        self.frappe.get_doc.return_value = remote
        with self.assertRaises(ValueError):
            self.editor.guardar_bpmn('Proceso', 'P1', 'manual.bpmn', xml())
        remote.get_content.assert_not_called()
        remote.save_file.assert_not_called()

    def test_malformed_input_is_rejected_before_reading_files(self):
        with self.assertRaises(ValueError):
            self.editor.guardar_bpmn('Proceso', 'P1', 'manual.bpmn', '<bpmn:definitions>')
        self.frappe.get_all.assert_not_called()


if __name__ == '__main__':
    unittest.main()
