"""Reintento limitado: nunca descartar escrituras previas del llamador."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class SerializationFailure(Exception):
    pgcode = '40001'


class TestReintento(unittest.TestCase):
    def setUp(self):
        self.frappe = types.ModuleType('frappe')
        self.frappe.whitelist = lambda **kwargs: lambda fn: fn
        self.frappe.db = Mock(transaction_writes=0)
        utils = types.ModuleType('frappe.utils')
        utils.now_datetime = Mock()
        spec = importlib.util.spec_from_file_location('ingesta_aislada', Path(__file__).resolve().parents[1] / 'sgc/ingesta.py')
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'frappe': self.frappe, 'frappe.utils': utils}):
            spec.loader.exec_module(self.module)

    def test_reinicia_snapshot_solo_antes_de_escribir(self):
        with patch.object(self.module, '_autorizar', side_effect=[SerializationFailure(), 'fuente']) as auth:
            self.assertEqual(self.module._autorizar_con_reintento('fuente'), 'fuente')
        self.assertEqual(auth.call_count, 2)
        self.frappe.db.rollback.assert_called_once()

    def test_no_descarta_escrituras_del_llamador(self):
        self.frappe.db.transaction_writes = 1
        with patch.object(self.module, '_autorizar', side_effect=SerializationFailure), self.assertRaises(SerializationFailure):
            self.module._autorizar_con_reintento('fuente')
        self.frappe.db.rollback.assert_not_called()

    def test_no_reintenta_otros_errores(self):
        with patch.object(self.module, '_autorizar', side_effect=ValueError), self.assertRaises(ValueError):
            self.module._autorizar_con_reintento('fuente')
        self.frappe.db.rollback.assert_not_called()

    def test_intentos_limitados(self):
        with patch.object(self.module, '_autorizar', side_effect=SerializationFailure) as auth, self.assertRaises(SerializationFailure):
            self.module._autorizar_con_reintento('fuente')
        self.assertEqual(auth.call_count, 3)
        self.assertEqual(self.frappe.db.rollback.call_count, 2)
