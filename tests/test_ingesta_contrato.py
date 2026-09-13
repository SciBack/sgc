import copy
import unittest

from sgc.ingesta_contrato import ErrorContrato, clave_medicion, evaluar_reglas, huella, normalizar_lote


def lote():
    return {'version': 1, 'fuente_dato': 'FUENTE-TEST', 'run_id': 'corrida-1',
            'extraido_en': '2026-09-13T05:00:00Z', 'mediciones': [
                {'indicador': 'IND-TEST', 'periodo_academico': '2026-II', 'valor_num': 0,
                 'unidad': '%', 'formula_version': 'v1', 'corte_inicio': '2026-08-01T00:00:00Z',
                 'corte_fin': '2026-09-12T23:59:59Z', 'estado_medicion': 'Provisional', 'cobertura_pct': 0}]}


class TestContrato(unittest.TestCase):
    def test_cero_y_cobertura_desconocida(self):
        d=normalizar_lote(lote())
        self.assertEqual(d['mediciones'][0]['cobertura_pct'],0)
        x=lote()
        del x['mediciones'][0]['cobertura_pct']
        self.assertIsNone(normalizar_lote(x)['mediciones'][0]['cobertura_pct'])

    def test_rechaza_no_finitos_booleanos_y_valor_ausente(self):
        for n in (float('nan'),float('inf'),True,None):
            x=lote()
            x['mediciones'][0]['valor_num']=n
            with self.assertRaises(ErrorContrato):
                normalizar_lote(x)

    def test_rechaza_campos_desconocidos_y_ambito_ambiguo(self):
        for changes in ({'ignore_permissions':True},{'programa_sede':'P-1','unidad_organica':'U-1'}):
            x=lote()
            x['mediciones'][0].update(changes)
            with self.assertRaises(ErrorContrato):
                normalizar_lote(x)

    def test_denominador_y_cobertura_invalidos(self):
        for changes in ({'denominador':0,'numerador':0},{'denominador':2},{'cobertura_pct':101},{'cobertura_pct':-1}):
            x=lote()
            x['mediciones'][0].update(changes)
            with self.assertRaises(ErrorContrato):
                normalizar_lote(x)

    def test_cortes_con_zona_y_orden(self):
        for changes in ({'corte_fin':'2026-09-12'}, {'corte_inicio':'2027-01-01T00:00:00Z'},
                        {'corte_fin':'2026-09-14T00:00:00Z'}):
            x=lote()
            x['mediciones'][0].update(changes)
            with self.assertRaises(ErrorContrato):
                normalizar_lote(x)

    def test_meta_completa(self):
        x=lote()
        x['mediciones'][0]['meta_valor']=20
        with self.assertRaises(ErrorContrato):
            normalizar_lote(x)

    def test_identidad_no_depende_del_valor(self):
        x=normalizar_lote(lote())
        y=copy.deepcopy(x)
        y['mediciones'][0]['valor_num']=10
        self.assertEqual(clave_medicion(x['fuente_dato'],x['mediciones'][0]),clave_medicion(y['fuente_dato'],y['mediciones'][0]))
        self.assertNotEqual(huella(x),huella(y))

    def test_duplicados_y_lote_vacio(self):
        x=lote()
        x['mediciones']*=2
        with self.assertRaises(ErrorContrato):
            normalizar_lote(x)
        x['mediciones']=[]
        with self.assertRaises(ErrorContrato):
            normalizar_lote(x)

    def test_reglas_obligatorio_cero_y_rango(self):
        m=normalizar_lote(lote())['mediciones'][0]
        self.assertEqual(evaluar_reglas(m,[{'name':'R','tipo_regla':'Obligatorio','campo_objetivo':'valor_num'}]),[])
        errores=evaluar_reglas(m,[{'name':'R','tipo_regla':'Rango','valor_min':1,'valor_max':100,'severidad':'Bloqueante','mensaje':'fuera de rango'}])
        self.assertEqual(errores[0]['regla'],'R')
        self.assertEqual(errores[0]['severidad'],'Bloqueante')

    def test_regla_no_soportada_falla_explicita(self):
        with self.assertRaises(ErrorContrato):
            evaluar_reglas({},[{'tipo_regla':'Coherencia entre campos','expresion':'__import__("os")'}])
