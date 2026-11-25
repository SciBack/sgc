"""Los diagramas BPMN del manual: se dibujan, no se desfasan y todo tutorial lleva el suyo.

Sin Frappe: `sgc.bpmn_svg` solo lee el XML de `docs/diagramas/bpmn/`.
"""

import importlib.util
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BPMN = RAIZ / "docs" / "diagramas" / "bpmn"
ASSETS = RAIZ / "docs-site" / "src" / "assets" / "bpmn"
TUTORIALES = RAIZ / "docs-site" / "src" / "content" / "docs" / "tutoriales"

_spec = importlib.util.spec_from_file_location("bpmn_svg", RAIZ / "sgc" / "bpmn_svg.py")
bpmn_svg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bpmn_svg)


class TestBpmnSvg(unittest.TestCase):
	def test_cada_bpmn_se_dibuja_como_svg_valido(self):
		bpmns = sorted(BPMN.glob("*.bpmn"))
		self.assertTrue(bpmns)
		for f in bpmns:
			with self.subTest(f.name):
				raiz = ET.fromstring(bpmn_svg.a_svg(f.read_bytes()))
				self.assertTrue(raiz.tag.endswith("svg"))
				# Cada tarea de usuario sale con su nombre.
				modelo = ET.fromstring(f.read_bytes())
				texto = " ".join(t.text or "" for t in raiz.iter("{http://www.w3.org/2000/svg}text"))
				for tarea in modelo.iter("{%s}userTask" % bpmn_svg.NS["bpmn"]):
					self.assertIn(tarea.get("name").split()[0], texto)

	def test_los_svg_del_manual_coinciden_con_los_bpmn(self):
		"""Regenerar: `for f in docs/diagramas/bpmn/*.bpmn; do python3 -m sgc.bpmn_svg $f docs-site/src/assets/bpmn/$(basename ${f%.bpmn}).svg; done`."""
		for f in sorted(BPMN.glob("*.bpmn")):
			with self.subTest(f.name):
				svg = ASSETS / f.with_suffix(".svg").name
				self.assertTrue(svg.exists(), f"Falta {svg.relative_to(RAIZ)}")
				self.assertEqual(svg.read_text(encoding="utf-8"), bpmn_svg.a_svg(f.read_bytes()),
				                 f"{svg.name} desfasado del .bpmn: regenerarlo")

	def test_todo_tutorial_lleva_su_diagrama_bpmn(self):
		"""Regla de Alberto (25-nov-2026): el flujo se ve de un vistazo en cada tutorial."""
		tutoriales = sorted(TUTORIALES.glob("*.md*"))
		self.assertTrue(tutoriales)
		for t in tutoriales:
			with self.subTest(t.name):
				refs = re.findall(r"!\[[^\]]+\]\(([^)]*assets/bpmn/[^)]+\.svg)\)", t.read_text(encoding="utf-8"))
				self.assertTrue(refs, f"{t.name} no lleva el diagrama BPMN de su flujo")
				for ref in refs:
					self.assertTrue((t.parent / ref).resolve().exists(), f"{t.name}: no existe {ref}")


if __name__ == "__main__":
	unittest.main()
