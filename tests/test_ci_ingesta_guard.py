"""El runner destructivo de fixtures solo puede abrir el sitio efímero de CI."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'deploy/ci_ingesta_transacciones.py'
spec = importlib.util.spec_from_file_location('runner_ci_ingesta', PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class TestGuardasRunnerIngesta(unittest.TestCase):
    def test_fuera_de_ci_rechaza_antes_de_leer_config(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, 'read_text') as read:
            with self.assertRaises(RuntimeError):
                runner.check_ci_site('/does-not-exist')
            read.assert_not_called()

    def test_guardas_ambiente_ruta_y_base(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / 'workspace'
            sites = workspace / 'frappe-bench' / 'sites'
            site = sites / 'test_site.localhost'
            site.mkdir(parents=True)
            valid = {'db_type': 'postgres', 'allow_tests': True, 'db_host': '127.0.0.1', 'db_port': 5432}
            config_path = site / 'site_config.json'
            config_path.write_text(json.dumps(valid))
            outside = Path(directory) / 'outside' / 'test_site.localhost'
            outside.mkdir(parents=True)
            (outside / 'site_config.json').write_text(json.dumps(valid))
            env = {'CI': 'true', 'GITHUB_ACTIONS': 'true', 'SGC_INGESTA_CI': '1', 'GITHUB_WORKSPACE': str(workspace)}
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(runner.check_ci_site(sites), str(sites.resolve()))
                with self.assertRaises(RuntimeError):
                    runner.check_ci_site(Path(directory) / 'outside')
                with patch.dict(os.environ, {'GITHUB_ACTIONS': 'false'}), self.assertRaises(RuntimeError):
                    runner.check_ci_site(sites)
                for changes in ({'db_host': '192.0.2.10'}, {'db_host': 'db.example.test'}, {'db_port': 5433}, {'db_port': None}, {'db_type': 'mariadb'}, {'allow_tests': False}):
                    config_path.write_text(json.dumps({**valid, **changes}))
                    with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                        runner.check_ci_site(sites)
                config_path.write_text(json.dumps({**valid, 'db_host': 'localhost', 'db_port': '5432'}))
                self.assertEqual(runner.check_ci_site(sites), str(sites.resolve()))


if __name__ == '__main__':
    unittest.main()
