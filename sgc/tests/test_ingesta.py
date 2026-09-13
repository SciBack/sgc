"""Contrato servidor: autenticación, lote atómico, idempotencia y linaje."""
import copy

import frappe
from frappe.tests import IntegrationTestCase

from sgc import ingesta
from sgc.tests import factories


class IntegrationTestIngesta(IntegrationTestCase):
    def tearDown(self):
        frappe.set_user('Administrator')

    def setUp(self):
        frappe.set_user('Administrator')
        self.indicador = factories.crear_indicador().name
        self.periodo = factories.crear_periodo_academico().name
        self.fuente = frappe.get_doc({
            'doctype': 'Fuente Dato', 'codigo': 'ING-'+frappe.generate_hash(length=8),
            'nombre': 'Fuente de pruebas', 'tipo': 'Data warehouse', 'responsable': 'Administrator',
            'usuario_ingesta': 'Administrator', 'codigo_publicacion': 'test-'+frappe.generate_hash(length=8),
            'confidencialidad': 'Interna', 'periodicidad': 'Diaria', 'metodo_recojo': 'Automático',
            'protocolo': 'REST', 'estado': 'Activa',
        }).insert(ignore_permissions=True)
        self.datos = {'version': 1, 'fuente_dato': self.fuente.name, 'run_id': 'run-1',
                      'extraido_en': '2026-09-13T05:00:00Z', 'mediciones': [self.medicion()]}

    def medicion(self):
        return {'indicador': self.indicador, 'periodo_academico': self.periodo,
                'valor_num': 0, 'unidad': '%', 'formula_version': 'v1', 'cobertura_pct': 0,
                'estado_medicion': 'Provisional', 'corte_inicio': '2026-09-01T00:00:00Z',
                'corte_fin': '2026-09-12T23:59:59Z'}

    def test_reintento_no_duplica_y_conflicto_no_reescribe(self):
        primero = ingesta.publicar_lote(self.datos)
        self.assertEqual(primero['estado'], 'Aceptado')
        self.assertEqual(ingesta.publicar_lote(self.datos), primero)
        vi = primero['mediciones'][0]
        self.assertEqual(frappe.db.get_value('Valor Indicador', vi, 'valor_num'), 0)
        self.datos['mediciones'][0]['valor_num'] = 50
        with self.assertRaises(frappe.ValidationError):
            ingesta.publicar_lote(self.datos)
        self.assertEqual(frappe.db.get_value('Valor Indicador', vi, 'valor_num'), 0)

    def test_rechazo_no_deja_filas_parciales(self):
        m = self.medicion()
        m['indicador'] = 'IND-NO-EXISTE'
        self.datos['mediciones'].append(m)
        r = ingesta.publicar_lote(self.datos)
        self.assertEqual(r['estado'], 'Rechazado')
        self.assertEqual(frappe.db.count('Valor Indicador', {'fuente_dato': self.fuente.name}), 0)
        self.assertEqual(frappe.get_doc('Lote Ingesta', r['lote']).estado, 'Rechazado')

    def test_periodo_cerrado_rechaza_pero_retry_aceptado_se_conserva(self):
        r = ingesta.publicar_lote(self.datos)
        frappe.db.set_value('Periodo Academico', self.periodo, 'estado', 'cerrado')
        self.assertEqual(ingesta.publicar_lote(self.datos), r)
        self.datos['run_id'] = 'run-2'
        self.assertEqual(ingesta.publicar_lote(self.datos)['estado'], 'Rechazado')

    def test_corte_antiguo_no_reemplaza_medicion(self):
        r = ingesta.publicar_lote(self.datos)
        self.datos['run_id'] = 'antiguo'
        self.datos['mediciones'][0]['corte_fin'] = '2026-09-11T00:00:00Z'
        self.datos['mediciones'][0]['valor_num'] = 99
        self.assertEqual(ingesta.publicar_lote(self.datos)['estado'], 'Rechazado')
        self.assertEqual(frappe.db.get_value('Valor Indicador', r['mediciones'][0], 'valor_num'), 0)

    def test_fuente_suspendida_y_usuario_no_autorizado(self):
        frappe.db.set_value('Fuente Dato', self.fuente.name, 'estado', 'Suspendida')
        with self.assertRaises(frappe.PermissionError):
            ingesta.publicar_lote(self.datos)
        frappe.db.set_value('Fuente Dato', self.fuente.name, 'estado', 'Activa')
        frappe.db.set_value('Fuente Dato', self.fuente.name, 'usuario_ingesta', 'Guest')
        with self.assertRaises(frappe.PermissionError):
            ingesta.publicar_lote(self.datos)

    def test_raw_documento_no_elude_api(self):
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({'doctype': 'Valor Indicador', 'indicador': self.indicador,
                            'periodo_academico': self.periodo, 'fuente': self.fuente.codigo_publicacion,
                            'valor_num': 5}).insert(ignore_permissions=True)
        r = ingesta.publicar_lote(self.datos)
        vi = frappe.get_doc('Valor Indicador', r['mediciones'][0])
        vi.ingesta_clave = None
        vi.fuente_dato = None
        vi.fuente = 'manual'
        with self.assertRaises(frappe.ValidationError):
            vi.save(ignore_permissions=True)

    def test_regla_bloqueante_y_advertencia(self):
        regla = frappe.get_doc({'doctype': 'Regla Validacion', 'codigo': 'RULE-'+frappe.generate_hash(length=8),
                                'nombre': 'Rango', 'fuente_dato': self.fuente.name, 'tipo_regla': 'Rango',
                                'valor_min': 1, 'valor_max': 100, 'severidad': 'Bloqueante',
                                'mensaje': 'Valor fuera de rango', 'activa': 1}).insert(ignore_permissions=True)
        self.assertEqual(ingesta.publicar_lote(self.datos)['estado'], 'Rechazado')
        regla.severidad = 'Advertencia'
        regla.save(ignore_permissions=True)
        self.datos['run_id'] = 'con-aviso'
        r = ingesta.publicar_lote(self.datos)
        self.assertEqual(r['estado'], 'Aceptado')
        self.assertEqual(len(r['advertencias']), 1)
        self.assertEqual(frappe.db.count('Alerta Indicador', {'valor_indicador': r['mediciones'][0]}), 1)
        ingesta.publicar_lote(self.datos)
        self.assertEqual(frappe.db.count('Alerta Indicador', {'valor_indicador': r['mediciones'][0]}), 1)

    def test_adopta_legacy_sin_cambiar_nombre(self):
        # Simula una medición anterior a configurar esta fuente para ingesta.
        frappe.db.set_value('Fuente Dato', self.fuente.name, 'usuario_ingesta', None)
        vi = factories.crear_valor_indicador(self.indicador, periodo_academico=self.periodo,
                                            fuente=self.fuente.codigo_publicacion, valor_num=10)
        frappe.db.set_value('Fuente Dato', self.fuente.name, 'usuario_ingesta', 'Administrator')
        r = ingesta.publicar_lote(self.datos)
        self.assertEqual(r['estado'], 'Aceptado')
        self.assertEqual(r['mediciones'], [vi.name])

    def test_legacy_no_elude_fuente_ni_periodo_anterior(self):
        frappe.db.set_value('Fuente Dato', self.fuente.name, 'usuario_ingesta', None)
        vi = factories.crear_valor_indicador(self.indicador, periodo_academico=self.periodo,
                                            fuente=self.fuente.codigo_publicacion, valor_num=10)
        frappe.db.set_value('Fuente Dato', self.fuente.name, 'usuario_ingesta', 'Administrator')
        vi.fuente = 'manual'
        with self.assertRaises(frappe.ValidationError):
            vi.save(ignore_permissions=True)
        frappe.db.set_value('Fuente Dato', self.fuente.name, 'usuario_ingesta', None)
        frappe.db.set_value('Periodo Academico', self.periodo, 'estado', 'cerrado')
        vi.periodo_academico = None
        with self.assertRaises(frappe.ValidationError):
            vi.save(ignore_permissions=True)

    def test_identidad_fuente_no_se_renombra(self):
        ingesta.publicar_lote(self.datos)
        with self.assertRaises(frappe.ValidationError):
            frappe.rename_doc('Fuente Dato', self.fuente.name, self.fuente.name + '-nueva', force=True)

    def test_productor_respeta_user_permission_indicador(self):
        usuario = frappe.get_doc({'doctype': 'User', 'email': 'ingesta-' + frappe.generate_hash(length=8) + '@example.test',
            'first_name': 'Productor de prueba', 'send_welcome_email': 0,
            'roles': [{'role': 'System Manager'}]}).insert(ignore_permissions=True)
        frappe.get_doc({'doctype': 'User Permission', 'user': usuario.name, 'allow': 'Indicador',
                        'for_value': self.indicador, 'apply_to_all_doctypes': 1}).insert(ignore_permissions=True)
        otro = factories.crear_indicador().name
        frappe.db.set_value('Fuente Dato', self.fuente.name, 'usuario_ingesta', usuario.name)
        frappe.clear_cache(user=usuario.name)
        frappe.set_user(usuario.name)
        self.assertEqual(ingesta.publicar_lote(self.datos)['estado'], 'Aceptado')
        self.datos['run_id'] = 'fuera-de-ambito'
        self.datos['mediciones'][0]['indicador'] = otro
        self.assertEqual(ingesta.publicar_lote(self.datos)['estado'], 'Rechazado')
