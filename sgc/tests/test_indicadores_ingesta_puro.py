"""Lectores de ingesta: unittest aislado, sin bench, credenciales ni base de datos."""
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class Row(dict):
    __getattr__ = dict.get


def load(path, name, modules):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


def structured(**changes):
    data = dict(indicador='ID6', periodo_academico='2026-I', programa_sede='MED-LIMA',
                unidad_organica=None, valor_num=50, unidad='%', formula_version='v1',
                corte_inicio='2026-01-01T00:00:00Z', corte_fin='2026-06-30T00:00:00Z',
                numerador=5, denominador=10, cobertura_pct=0, meta_valor=60,
                meta_operador='>=', meta_unidad='%', estado_medicion='Provisional')
    data.update(changes)
    return Row(name='V1', indicador='ID6', programa_sede='MED-LIMA', periodo_academico='2026-I',
               valor_num=50, fecha=None, calculado=1, fuente='dw', ingesta_clave='key',
               datos_ingesta=json.dumps(data), valor_texto='DW v1-norma Viejo · n=999 · meta 20% (cumple)')


class TestLectoresIngesta(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType('frappe')
        self.frappe._ = lambda value: value
        self.frappe._dict = Row
        self.ia = load(ROOT / 'indicadores_acreditacion.py', 'lector_aislado', {'frappe': self.frappe})
        self.report = load(ROOT / 'sgc_nucleo/report/indicadores_de_acreditacion/indicadores_de_acreditacion.py',
                           'reporte_aislado', {'frappe': self.frappe, 'sgc.indicadores_acreditacion': self.ia})

    def test_prefiere_json_sobre_prosa_obsoleta(self):
        result = self.ia._leer_medicion(structured())
        self.assertEqual(result['n'], 10)
        self.assertEqual(result['meta_texto'], '>= 60%')
        self.assertFalse(result['cumple'])
        self.assertEqual(result['cobertura'], 0)
        self.assertTrue(result['provisional'])
        self.assertEqual(result['marco'], '')

    def test_invalid_json_never_recovers_old_text(self):
        for raw in ('{', '[]', '{}', 'null', '', None):
            with self.subTest(raw=raw):
                row = structured()
                row['datos_ingesta'] = raw
                result = self.ia._leer_medicion(row)
                self.assertIsNone(result['cumple'])
                self.assertIsNone(result['n'])
                self.assertIsNone(result['cobertura'])
                self.assertTrue(result['provisional'])
                self.assertFalse(result['contrato_reconocido'])
                self.assertTrue(result['error_ingesta'])

    def test_semantically_invalid_data_is_unknown(self):
        for changes in ({'cobertura_pct': -1}, {'denominador': 0}, {'valor_num': float('nan')}):
            with self.subTest(changes=changes):
                self.assertTrue(self.ia._leer_medicion(structured(**changes))['error_ingesta'])

    def test_judgment_requires_matching_units_and_meta(self):
        for changes in ({'meta_unidad': 'años'}, {'meta_valor': None, 'meta_operador': None, 'meta_unidad': None}):
            with self.subTest(changes=changes):
                self.assertIsNone(self.ia._leer_medicion(structured(**changes))['cumple'])
        for operator, target, expected in (('>', 50, False), ('>=', 50, True), ('<', 50, False), ('<=', 50, True), ('=', 50, True)):
            self.assertEqual(self.ia._leer_medicion(structured(meta_operador=operator, meta_valor=target))['cumple'], expected)

    def test_unknown_coverage_never_means_validated(self):
        result = self.ia._leer_medicion(structured(cobertura_pct=None, estado_medicion='Validado'))
        self.assertIsNone(result['cobertura'])
        self.assertTrue(result['provisional'])
        self.assertFalse(self.ia._leer_medicion(structured(cobertura_pct=100, estado_medicion='Validado'))['provisional'])

    def test_no_impone_umbral_del_productor_dw(self):
        self.assertFalse(self.ia._leer_medicion(structured(cobertura_pct=90, estado_medicion='Validado'))['provisional'])

    def test_legacy_behavior_exact_without_key(self):
        row = structured()
        row['ingesta_clave'] = None
        self.assertEqual(self.ia._leer_medicion(row), self.ia._parsear_valor_texto(row['valor_texto']))

    def test_report_consumes_structured_and_requests_fields(self):
        self.frappe.get_all = Mock(side_effect=[[structured()], [Row(name='ID6', nombre='Nombre')], []])
        result = self.report.execute({'fuente': 'dw'})[1][0]
        self.assertEqual(result['muestra'], 10)
        self.assertEqual(result['meta'], '>= 60%')
        self.assertEqual(result['cumple'], 'No')
        self.assertEqual(result['provisional'], 1)
        self.assertIn('datos_ingesta', self.frappe.get_all.call_args_list[0].kwargs['fields'])

    def test_ae_consumes_structured_unit_not_old_catalog(self):
        self.frappe.get_all = Mock(return_value=[structured(unidad='años', meta_unidad='años')])
        with patch.object(self.ia, '_par_de_autoevaluacion', return_value={'programa_sede': 'MED-LIMA', 'periodo_academico': '2026-I'}), patch.object(self.ia, '_nombres_de_indicador', return_value={'ID6': 'Nombre'}), patch.object(self.ia, '_unidades_de_indicador', return_value={'ID6': '%'}):
            result = self.ia.indicadores_de_autoevaluacion('AE', fuente='dw')['filas'][0]
        self.assertEqual(result['unidad'], 'años')
        self.assertEqual(result['n'], 10)
        self.assertIn('datos_ingesta', self.frappe.get_all.call_args.kwargs['fields'])


if __name__ == '__main__':
    unittest.main()
