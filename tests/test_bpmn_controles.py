"""Controles operativos visibles: estructura, ubicación y trazabilidad al código."""
import ast
import importlib.util
import sys
import types
import unittest
from itertools import pairwise
from pathlib import Path
from unittest.mock import Mock, patch
from xml.etree import ElementTree as ET

from sgc import bpmn

ROOT = Path(__file__).resolve().parents[1]
NS = bpmn.NS


class TestControlesBpmn(unittest.TestCase):
    def diagram(self, doctype):
        spec = next(s for _, s in bpmn.specs_de_workflows() if s['document_type'] == doctype)
        return ET.fromstring(bpmn.construir(spec)), spec

    def test_controles_visibles_con_origen_resoluble(self):
        for doctype in ('Evidencia', 'Autoevaluacion', 'No Conformidad', 'Accion Mejora'):
            root, _ = self.diagram(doctype)
            notes = root.findall('.//bpmn:textAnnotation', NS)
            self.assertTrue(notes, doctype)
            for note in notes:
                self.assertTrue(note.find('bpmn:text', NS).text)
                origin = note.find('bpmn:documentation', NS).text
                module, cls, method = origin.rsplit('.', 2)
                tree = ast.parse((ROOT / (module.replace('.', '/') + '.py')).read_text())
                target = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
                self.assertTrue(any(isinstance(n, ast.FunctionDef) and n.name == method for n in target.body), origin)

    def test_cierre_interpone_efecto_sin_nueva_accion_humana(self):
        root, spec = self.diagram('Autoevaluacion')
        effect = root.find('.//bpmn:serviceTask', NS)
        self.assertIsNotNone(effect)
        self.assertIn('before_submit', effect.find('bpmn:documentation', NS).text)
        flows = root.findall('.//bpmn:sequenceFlow', NS)
        self.assertTrue(any(f.get('sourceRef') == 'Task_Consolidada__Cerrar' and f.get('targetRef') == effect.get('id') for f in flows))
        self.assertTrue(any(f.get('sourceRef') == effect.get('id') and f.get('targetRef') == 'End_Cerrada' for f in flows))
        self.assertEqual(len(root.findall('.//bpmn:userTask', NS)), len(spec['transitions']))
        texts = '\n'.join(n.text for n in root.findall('.//bpmn:text', NS))
        self.assertIn('confirmados', texts)
        self.assertIn('Al guardar', texts)

    def test_tareas_automaticas_rectangulares_descartan_cajas_de_evento(self):
        for doctype in ('Autoevaluacion', 'Aplicacion Instrumento', 'Documento Controlado'):
            root, spec = self.diagram(doctype)
            effects = root.findall('.//bpmn:serviceTask', NS)
            self.assertTrue(effects, doctype)
            previous = bpmn.layout_de(bpmn.construir(spec))
            for effect in effects:
                box = previous[effect.get('id')]
                self.assertEqual(box[2:], (bpmn.ANCHO_TAREA, bpmn.ALTO_TAREA))
                # Reproduce el XML existente: evento 36x36 centrado en el carril.
                x, y, _width, height = box
                previous[effect.get('id')] = (x, y + (height - 36) / 2, 36, 36)
            regenerated = bpmn.layout_de(bpmn.construir(spec, layout_previo=previous))
            for effect in effects:
                self.assertEqual(regenerated[effect.get('id')][2:],
                                 (bpmn.ANCHO_TAREA, bpmn.ALTO_TAREA))

    def test_flechas_no_atraviesan_cajas_en_los_quince_diagramas(self):
        for _, spec in bpmn.specs_de_workflows():
            root = ET.fromstring(bpmn.construir(spec))
            kinds = ('userTask', 'serviceTask', 'startEvent', 'endEvent',
                     'exclusiveGateway', 'intermediateCatchEvent')
            node_ids = {n.get('id') for kind in kinds for n in root.findall('.//bpmn:' + kind, NS)}
            boxes = {key: value for key, value in bpmn.layout_de(bpmn.construir(spec)).items() if key in node_ids}
            flow_ids = {f.get('id') for f in root.findall('.//bpmn:sequenceFlow', NS)}
            for edge in root.findall('.//bpmndi:BPMNEdge', NS):
                if edge.get('bpmnElement') not in flow_ids:
                    continue
                points = [(float(p.get('x')), float(p.get('y'))) for p in edge.findall('di:waypoint', NS)]
                for (x1, y1), (x2, y2) in pairwise(points):
                    self.assertTrue(x1 == x2 or y1 == y2)
                    for name, (x, y, w, h) in boxes.items():
                        crossed = (x < x1 < x + w and max(min(y1, y2), y) < min(max(y1, y2), y + h)
                                   if x1 == x2 else
                                   y < y1 < y + h and max(min(x1, x2), x) < min(max(x1, x2), x + w))
                        self.assertFalse(crossed, (spec['document_type'], edge.get('bpmnElement'), name))

    def test_controlador_ejecuta_snapshot_y_vigencia_en_mismo_submit(self):
        # Ejecutar el controlador real con dependencias aisladas: no basta con
        # que el nombre de before_submit exista en el XML o en el AST.
        frappe = types.ModuleType('frappe')
        frappe._ = lambda text: text
        frappe.whitelist = lambda: lambda fn: fn
        frappe.throw = Mock(side_effect=ValueError('cierre incompleto'))
        document = types.ModuleType('frappe.model.document')
        document.Document = object
        scoring = types.ModuleType('sgc.scoring')
        scoring.construir_snapshot = Mock(return_value='snapshot-ficticio')
        confirmacion = types.ModuleType('sgc.confirmacion')
        confirmacion.calcular_vigencia_oficial = Mock(return_value={'ok': True, 'vigencia': '3 años'})
        path = ROOT / 'sgc/sgc_nucleo/doctype/autoevaluacion/autoevaluacion.py'
        spec = importlib.util.spec_from_file_location('ae_aislada_bpmn', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': frappe, 'frappe.model.document': document,
                                     'sgc.scoring': scoring, 'sgc.confirmacion': confirmacion}):
            spec.loader.exec_module(module)
            ae = module.Autoevaluacion()
            ae.name = 'AE-FICTICIA'
            ae.before_submit()
            self.assertEqual(ae.marco_snapshot, 'snapshot-ficticio')
            self.assertEqual(ae.resultado_vigencia, '3 años')
            scoring.construir_snapshot.assert_called_once_with(ae.name)
            confirmacion.calcular_vigencia_oficial.assert_called_once_with(ae.name)
            confirmacion.calcular_vigencia_oficial.return_value = {'ok': False, 'faltan': 1}
            with self.assertRaises(ValueError):
                ae.before_submit()

    def test_anotaciones_sin_solapes_y_regeneracion_estable(self):
        for doctype in ('Evidencia', 'Autoevaluacion', 'No Conformidad', 'Accion Mejora'):
            root, spec = self.diagram(doctype)
            boxes = {}
            for shape in root.findall('.//bpmndi:BPMNShape', NS):
                bound = shape.find('dc:Bounds', NS)
                boxes[shape.get('bpmnElement')] = tuple(float(bound.get(k)) for k in ('x', 'y', 'width', 'height'))
            for note in root.findall('.//bpmn:textAnnotation', NS):
                x, y, w, h = boxes[note.get('id')]
                self.assertGreaterEqual(w, 350)
                for other, (ox, oy, ow, oh) in boxes.items():
                    if other != note.get('id'):
                        self.assertFalse(x < ox + ow and ox < x + w and y < oy + oh and oy < y + h, (doctype, other))
            first = bpmn.construir(spec)
            self.assertEqual(first, bpmn.construir(spec, layout_previo=bpmn.layout_de(first)))
