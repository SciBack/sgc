"""Pruebas de deploy/check_version.py (#52), sin Frappe."""

import tempfile
import unittest
from pathlib import Path

import check_version as cv

CHANGELOG = """# Cambios

## [Sin publicar]

## [1.2.0] - 2026-11-02

Algo nuevo.

## [1.1.0] - 2026-10-20
"""


class TestCheckVersion(unittest.TestCase):
	def setUp(self):
		self._tmp = tempfile.TemporaryDirectory()
		self.raiz = Path(self._tmp.name)
		(self.raiz / "sgc").mkdir()
		self._version("1.2.0")
		(self.raiz / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")

	def tearDown(self):
		self._tmp.cleanup()

	def _version(self, v):
		(self.raiz / "sgc" / "__init__.py").write_text(f'__version__ = "{v}"\n', encoding="utf-8")

	def test_tag_y_version_coinciden(self):
		self.assertEqual(cv.comprobar(self.raiz, tag="v1.2.0"), "1.2.0")

	def test_publicar_con_desajuste_falla(self):
		with self.assertRaisesRegex(cv.Incoherencia, "no coincide"):
			cv.comprobar(self.raiz, tag="v1.2.1")

	def test_tag_sin_forma_de_version_falla(self):
		for tag in ("1.2.0", "v1.2", "release-1.2.0", "v1.2.0-rc1"):
			with self.subTest(tag=tag), self.assertRaisesRegex(cv.Incoherencia, "vX.Y.Z"):
				cv.comprobar(self.raiz, tag=tag)

	def test_version_sin_entrada_en_el_changelog_falla(self):
		self._version("1.3.0")
		with self.assertRaisesRegex(cv.Incoherencia, "CHANGELOG"):
			cv.comprobar(self.raiz)

	def test_entrada_sin_fecha_no_cuenta(self):
		(self.raiz / "CHANGELOG.md").write_text("## [1.2.0]\n", encoding="utf-8")
		with self.assertRaisesRegex(cv.Incoherencia, "CHANGELOG"):
			cv.comprobar(self.raiz)

	def test_version_que_no_es_semantica_falla(self):
		self._version("1.2")
		with self.assertRaisesRegex(cv.Incoherencia, "semántica"):
			cv.comprobar(self.raiz)

	def test_el_repositorio_es_coherente(self):
		"""El propio repositorio: lo que se mergea a main ya tiene su entrada."""
		self.assertTrue(cv.SEMVER.match(cv.comprobar()))


if __name__ == "__main__":
	unittest.main()
