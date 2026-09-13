"""El control de deriva debe detectar cambios, ausencias y diagramas huérfanos."""

import shutil
import tempfile
import unittest
from pathlib import Path

from check_bpmn import comprobar


class TestConcordancia(unittest.TestCase):
	def setUp(self):
		self.temp = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp.cleanup)
		self.destino = Path(self.temp.name)
		origen = Path(__file__).resolve().parents[1] / "docs/diagramas/bpmn"
		for archivo in origen.glob("*.bpmn"):
			shutil.copyfile(archivo, self.destino / archivo.name)

	def test_versionados_concuerdan(self):
		self.assertEqual(comprobar(self.destino), [])

	def test_detecta_cambio_semantico(self):
		archivo = next(self.destino.glob("*.bpmn"))
		xml = archivo.read_text()
		archivo.write_text(xml.replace('name="', 'name="DERIVA ', 1))
		self.assertTrue(any("Diverge" in e for e in comprobar(self.destino)))

	def test_detecta_falta_y_huerfano(self):
		archivo = next(self.destino.glob("*.bpmn"))
		archivo.rename(self.destino / "99-huerfano.bpmn")
		errores = comprobar(self.destino)
		self.assertTrue(any("Falta:" in e for e in errores))
		self.assertTrue(any("Sin workflow" in e for e in errores))
