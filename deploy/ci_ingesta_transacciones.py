#!/usr/bin/env python3
"""Pruebas WSGI/PostgreSQL reales, EXCLUSIVAS del sitio efímero de GitHub CI.

Runner separado: confirma fixtures propias y deja commit/rollback de requests a
frappe.app.application. No ejecutar mediante IntegrationTestCase ni en producción.
"""
import copy
import json
import multiprocessing
import os
import queue
import secrets
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

SITE = 'test_site.localhost'
TIMEOUT = 90


def check_ci_site(sites_path):
    if (os.environ.get('CI') != 'true' or os.environ.get('GITHUB_ACTIONS') != 'true'
            or os.environ.get('SGC_INGESTA_CI') != '1' or not os.environ.get('GITHUB_WORKSPACE')):
        raise RuntimeError('Runner exclusivo de GitHub Actions con opt-in y workspace explícitos')
    path = Path(sites_path).resolve()
    expected = Path(os.environ['GITHUB_WORKSPACE']).resolve() / 'frappe-bench' / 'sites'
    if path != expected or (path / SITE).resolve().parent != path:
        raise RuntimeError('Sitio fuera de GITHUB_WORKSPACE/frappe-bench/sites')
    config = json.loads((path / SITE / 'site_config.json').read_text())
    if config.get('db_type') != 'postgres' or config.get('allow_tests') not in (True, 1):
        raise RuntimeError('Se requiere PostgreSQL y allow_tests en test_site.localhost')
    if config.get('db_host') not in ('127.0.0.1', 'localhost') or str(config.get('db_port')) != '5432':
        raise RuntimeError('Solo se permite PostgreSQL local en el puerto 5432 de CI')
    return str(path)


def connect(sites_path):
    check_ci_site(sites_path)
    import frappe
    frappe.init(site=SITE, sites_path=sites_path, force=True)
    frappe.connect()
    frappe.set_user('Administrator')
    return frappe


def request_worker(sites_path, token, payload, barrier, output, inject_failure=False, pids=None, slot=0, winner=None):
    """Un proceso y una conexión propia; no se reemplaza ningún método de DB."""
    try:
        check_ci_site(sites_path)
        os.chdir(sites_path)
        os.environ['SITES_PATH'] = sites_path
        import frappe
        import frappe.app
        from frappe.model.document import Document
        from werkzeug.test import Client
        from werkzeug.wrappers import Response

        from sgc import ingesta

        observed = {}
        original_authorize = ingesta._autorizar
        original_save = Document.save
        saved_count = 0

        def synchronized_authorize(name):
            # Connection IDs prove these are independent request transactions.
            observed['backend_pid'] = frappe.db.sql('SELECT pg_backend_pid()')[0][0]
            initial_attempt = 'attempts' not in observed
            observed['attempts'] = observed.get('attempts', 0) + 1
            if barrier is not None and initial_attempt:
                pids[slot] = observed['backend_pid']
                barrier.wait(timeout=30)
            source = original_authorize(name)
            if barrier is not None:
                with winner.get_lock():
                    first = winner.value == 0
                    if first:
                        winner.value = observed['backend_pid']
                if first:
                    # Hold the actual source row lock until PG confirms the peer
                    # is blocked by this connection, not merely scheduled later.
                    peer = pids[1 - slot]
                    deadline = time.monotonic() + 20
                    while time.monotonic() < deadline:
                        blocked = frappe.db.sql('SELECT %s = ANY(pg_blocking_pids(%s))',
                                                (observed['backend_pid'], peer))[0][0]
                        if blocked:
                            observed['blocked_peer'] = True
                            break
                        time.sleep(0.05)
                    else:
                        raise RuntimeError('No se observó contención real del bloqueo por fuente')
            return source

        def fail_on_second_measurement(doc, *args, **kwargs):
            nonlocal saved_count
            if doc.doctype == 'Valor Indicador':
                saved_count += 1
                if saved_count == 2:
                    # Evidence from the uncommitted request, before the failure:
                    # a batch, a measurement and its warning really exist in PG.
                    observed['partial'] = {
                        'lotes': frappe.db.count('Lote Ingesta', {'fuente_dato': payload['fuente_dato']}),
                        'valores': frappe.db.count('Valor Indicador', {'fuente_dato': payload['fuente_dato']}),
                        'alertas': frappe.db.count('Alerta Indicador', {
                            'indicador': ['in', [m['indicador'] for m in payload['mediciones']]],
                        }),
                    }
                    raise RuntimeError('CI_INJECTED_AFTER_FIRST_MEASUREMENT')
            return original_save(doc, *args, **kwargs)

        client = Client(frappe.app.application, Response, use_cookies=False)
        with patch.object(ingesta, '_autorizar', synchronized_authorize):
            with patch.object(Document, 'save', fail_on_second_measurement if inject_failure else original_save):
                response = client.post(
                    '/api/method/sgc.ingesta.publicar_lote',
                    base_url=f'http://{SITE}',
                    headers={'X-Frappe-Site-Name': SITE, 'Authorization': f'token {token}',
                             'Accept': 'application/json'},
                    json={'lote': payload},
                )
                body = response.get_json(silent=True) or {}
                observed.update(status=response.status_code, message=body.get('message'),
                                exc_type=body.get('exc_type'))
                response.close()  # executes WSGI after_response + frappe.destroy
        output.put(observed)
    except BaseException as exc:
        # No tokens, request headers or traceback locals in CI output.
        output.put({'worker_error': type(exc).__name__, 'detail': str(exc)[:250]})


class TestIngestaTransaccionesReales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sites_path = check_ci_site(os.environ.get('SITES_PATH', '.'))

    def setUp(self):
        self.created = []
        self.source = None
        self.indicators = []
        self.addCleanup(self.cleanup_fixtures)
        frappe = connect(self.sites_path)
        from frappe.permissions import add_permission, update_permission_property
        try:
            suffix = uuid.uuid4().hex[:12]
            self.role = f'CI-Ingesta-{suffix}'
            self.user = f'ingesta-{suffix}@example.test'
            self.insert({'doctype': 'Role', 'role_name': self.role, 'desk_access': 1})
            add_permission('Valor Indicador', self.role, 0)
            for permission in ('read', 'write', 'create'):
                update_permission_property('Valor Indicador', self.role, 0, permission, 1)
            key, secret = secrets.token_hex(12), secrets.token_hex(24)
            self.insert({'doctype': 'User', 'email': self.user, 'first_name': 'Productor ficticio CI',
                         'send_welcome_email': 0, 'api_key': key, 'api_secret': secret,
                         'roles': [{'role': self.role}]})
            self.token = key + ':' + secret
            self.period = self.insert({'doctype': 'Periodo Academico', 'codigo': f'CI-{suffix}-2026-I',
                                       'anio': 2026, 'semestre': 'I', 'estado': 'abierto'}).name
            for number in range(2):
                self.indicators.append(self.insert({'doctype': 'Indicador', 'codigo': f'CI-{suffix}-{number}',
                    'nombre': f'Indicador ficticio {number}', 'categoria': 'Acreditacion'}).name)
            self.source = self.insert({
                'doctype': 'Fuente Dato', 'codigo': f'CI-{suffix}', 'nombre': 'Fuente ficticia CI',
                'tipo': 'Data warehouse', 'responsable': 'Administrator', 'usuario_ingesta': self.user,
                'codigo_publicacion': f'ci-{suffix}', 'confidencialidad': 'Interna',
                'periodicidad': 'Diaria', 'metodo_recojo': 'Automático', 'protocolo': 'REST', 'estado': 'Activa',
            }).name
            self.payload = {'version': 1, 'fuente_dato': self.source, 'run_id': 'concurrent-1',
                'extraido_en': '2026-09-13T05:00:00Z', 'mediciones': [self.measurement(self.indicators[0])]}
            frappe.db.commit()  # own fixtures only; never inside IntegrationTestCase
            frappe.clear_cache(user=self.user)
        finally:
            frappe.destroy()

    def insert(self, values):
        import frappe
        doc = frappe.get_doc(values).insert(ignore_permissions=True)
        self.created.append((doc.doctype, doc.name))
        return doc

    def measurement(self, indicator, value=10):
        return {'indicador': indicator, 'periodo_academico': self.period, 'valor_num': value,
                'unidad': '%', 'formula_version': 'ci-v1', 'cobertura_pct': 100,
                'estado_medicion': 'Validado', 'corte_inicio': '2026-09-01T00:00:00Z',
                'corte_fin': '2026-09-12T23:59:59Z'}

    def cleanup_fixtures(self):
        frappe = connect(self.sites_path)
        try:
            # Bypass immutable guards only for exact UUID-scoped CI fixtures.
            # Capture names BEFORE deleting documents, including their Version rows.
            version_refs = {}
            for doctype, name in self.created:
                version_refs.setdefault(doctype, set()).add(name)
            scoped = []
            if self.indicators:
                scoped.append(('Alerta Indicador', {'indicador': ['in', self.indicators]}))
            if self.source:
                scoped.extend((doctype, {'fuente_dato': self.source}) for doctype in
                              ('Valor Indicador', 'Lote Ingesta', 'Regla Validacion'))
            for doctype, filters in scoped:
                names = frappe.get_all(doctype, filters=filters, pluck='name')
                if names:
                    version_refs.setdefault(doctype, set()).update(names)
                    frappe.db.delete('Version', {'ref_doctype': doctype, 'docname': ['in', names]})
                    frappe.db.delete(doctype, {'name': ['in', names]})
            if hasattr(self, 'role'):
                frappe.db.delete('Custom DocPerm', {'role': self.role})
            for doctype, name in reversed(self.created):
                # Normal deletion cleans child tables and encrypted User credentials.
                if frappe.db.exists(doctype, name):
                    frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
            for doctype, names in version_refs.items():
                filters = {'ref_doctype': doctype, 'docname': ['in', sorted(names)]}
                frappe.db.delete('Version', filters)
                self.assertEqual(frappe.db.count('Version', filters), 0,
                                 f'Versiones huérfanas de fixtures CI: {doctype}')
            frappe.db.commit()
        finally:
            frappe.destroy()

    def requests(self, payloads, inject_failure=False):
        ctx = multiprocessing.get_context('spawn')
        barrier = ctx.Barrier(len(payloads)) if len(payloads) > 1 else None
        output = ctx.Queue()
        pids = ctx.Array('i', len(payloads))
        winner = ctx.Value('i', 0)
        workers = [ctx.Process(target=request_worker,
                    args=(self.sites_path, self.token, payload, barrier, output, inject_failure, pids, slot, winner))
                   for slot, payload in enumerate(payloads)]
        try:
            for worker in workers:
                worker.start()
            deadline = time.monotonic() + TIMEOUT
            results = []
            for _ in workers:
                try:
                    results.append(output.get(timeout=max(0.1, deadline - time.monotonic())))
                except queue.Empty:
                    self.fail('Timeout de requests WSGI concurrentes')
            for worker in workers:
                worker.join(timeout=max(0.1, deadline - time.monotonic()))
                self.assertFalse(worker.is_alive(), 'Worker no terminó')
                self.assertEqual(worker.exitcode, 0)
            for result in results:
                self.assertNotIn('worker_error', result, result)
                self.assertIn('backend_pid', result, result)
            self.assertEqual(len({r['backend_pid'] for r in results}), len(workers), results)
            if len(workers) > 1:
                self.assertEqual(sum(bool(r.get('blocked_peer')) for r in results), 1, results)
            return results
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join(timeout=5)
                if worker.is_alive():
                    worker.kill()
                    worker.join(timeout=5)
            output.close()
            output.join_thread()

    def snapshot(self):
        frappe = connect(self.sites_path)
        try:
            return {
                'lotes': frappe.get_all('Lote Ingesta', filters={'fuente_dato': self.source},
                    fields=['name', 'estado', 'respuesta']),
                'valores': frappe.get_all('Valor Indicador', filters={'fuente_dato': self.source},
                    fields=['name', 'ingesta_clave', 'lote_ingesta', 'valor_num', 'formula_version', 'datos_ingesta']),
                'alertas': frappe.db.count('Alerta Indicador', {'indicador': ['in', self.indicators]}),
            }
        finally:
            frappe.destroy()

    def test_same_run_has_one_batch_one_measurement_same_response(self):
        responses = self.requests([self.payload, copy.deepcopy(self.payload)])
        self.assertEqual([r['status'] for r in responses], [200, 200], responses)
        self.assertEqual(responses[0]['message'], responses[1]['message'])
        self.assertEqual(responses[0]['message']['estado'], 'Aceptado')
        state = self.snapshot()
        self.assertEqual(len(state['lotes']), 1)
        self.assertEqual(len(state['valores']), 1)
        self.assertEqual(state['valores'][0]['name'], responses[0]['message']['mediciones'][0])

    def test_distinct_runs_share_identity_without_corruption(self):
        second = copy.deepcopy(self.payload)
        second['run_id'] = 'concurrent-2'
        second['mediciones'][0]['valor_num'] = 20
        second['mediciones'][0]['formula_version'] = 'ci-v2'
        responses = self.requests([self.payload, second])
        self.assertEqual([r['status'] for r in responses], [200, 200], responses)
        self.assertTrue(all(r['message']['estado'] == 'Aceptado' for r in responses))
        self.assertEqual(responses[0]['message']['mediciones'], responses[1]['message']['mediciones'])
        state = self.snapshot()
        self.assertEqual(len(state['lotes']), 2)
        self.assertEqual(len(state['valores']), 1)
        value = state['valores'][0]
        contract = json.loads(value['datos_ingesta'])
        self.assertIn(value['valor_num'], (10, 20))
        self.assertEqual(contract['valor_num'], value['valor_num'])
        self.assertTrue(value['ingesta_clave'])
        from sgc.ingesta_contrato import huella
        expected = {huella([self.source, 'concurrent-1']): (10, 'ci-v1'),
                    huella([self.source, 'concurrent-2']): (20, 'ci-v2')}
        self.assertEqual((value['valor_num'], value['formula_version']), expected[value['lote_ingesta']])
        self.assertEqual(contract['formula_version'], value['formula_version'])
        self.assertIn(value['lote_ingesta'], {b['name'] for b in state['lotes']})
        self.assertTrue(all(json.loads(b['respuesta'])['mediciones'] == [value['name']] for b in state['lotes']))

    def test_unexpected_failure_rolls_back_full_wsgi_request(self):
        frappe = connect(self.sites_path)
        try:
            self.insert({'doctype': 'Regla Validacion', 'codigo': 'CI-RULE-' + uuid.uuid4().hex[:12],
                'nombre': 'Advertencia ficticia', 'fuente_dato': self.source, 'tipo_regla': 'Rango',
                'campo_objetivo': 'valor_num', 'valor_min': 100, 'valor_max': 200,
                'severidad': 'Advertencia', 'mensaje': 'Advertencia de prueba CI', 'activa': 1})
            frappe.db.commit()
        finally:
            frappe.destroy()
        self.payload['mediciones'].append(self.measurement(self.indicators[1], 20))
        response = self.requests([self.payload], inject_failure=True)[0]
        self.assertEqual(response['partial'], {'lotes': 1, 'valores': 1, 'alertas': 1})
        self.assertEqual(response['status'], 500, response)
        self.assertEqual(response['exc_type'], 'RuntimeError')
        self.assertEqual(self.snapshot(), {'lotes': [], 'valores': [], 'alertas': 0})


if __name__ == '__main__':
    unittest.main(verbosity=2)
