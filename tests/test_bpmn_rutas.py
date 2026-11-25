"""Las flechas ordenadas a mano en un `.bpmn` sobreviven a la regeneración, si siguen siendo válidas.

Sin Frappe: los specs se leen del código con `ast`.
"""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from sgc.bpmn import _ruta_valida, construir, layout_de, nombre_archivo, specs_de_workflows

BPMN = RAIZ / "docs" / "diagramas" / "bpmn"


def _spec(document_type):
	return next(s for _, s in specs_de_workflows() if s["document_type"] == document_type)


class TestRutasAMano(unittest.TestCase):
	def setUp(self):
		self.spec = _spec("Autoevaluacion")
		self.xml = (BPMN / nombre_archivo("Autoevaluacion")).read_text(encoding="utf-8")
		self.layout = layout_de(self.xml)
		self.fid = "Flow_gw_En_revision_Consolidar"

	def test_regenerar_conserva_las_flechas_del_fichero(self):
		regenerado = layout_de(construir(self.spec, layout_previo=self.layout))
		rutas = [k for k in self.layout if k.startswith("ruta:")]
		self.assertTrue(rutas)
		for k in rutas:
			self.assertEqual(regenerado[k], self.layout[k], k)

	def test_una_flecha_que_atraviesa_una_caja_se_recalcula(self):
		layout = dict(self.layout)
		x = layout["Task_En_revision__Consolidar"][0]
		gw = layout["Gateway_En_revision"]
		# Del gateway en línea recta por DENTRO de «Devolver a evaluación».
		mala = ((gw[0] + gw[2], gw[1] + gw[3] / 2), (x, gw[1] + gw[3] / 2))
		layout[f"ruta:{self.fid}"] = mala
		regenerado = layout_de(construir(self.spec, layout_previo=layout))
		self.assertNotEqual(regenerado[f"ruta:{self.fid}"], mala)

	def test_una_flecha_que_no_llega_a_su_destino_se_recalcula(self):
		layout = dict(self.layout)
		layout[f"ruta:{self.fid}"] = ((0.0, 0.0), (0.0, 50.0))
		regenerado = layout_de(construir(self.spec, layout_previo=layout))
		self.assertNotEqual(regenerado[f"ruta:{self.fid}"], ((0.0, 0.0), (0.0, 50.0)))

	def test_regenerar_conserva_los_carriles_agrandados(self):
		"""Se agrandan carriles para que quepan las flechas: eso también se queda."""
		regenerado = layout_de(construir(self.spec, layout_previo=self.layout))
		for k, v in self.layout.items():
			if k.startswith("Lane_"):
				self.assertEqual(regenerado[k], v, k)

	def test_un_carril_que_deja_cajas_fuera_vuelve_a_su_medida(self):
		layout = dict(self.layout)
		carril = next(k for k in layout if k.startswith("Lane_DPGC"))
		x, y, w, _h = layout[carril]
		layout[carril] = (x, y, w, 100.0)  # las cajas de la DPGC ya no caben
		regenerado = layout_de(construir(self.spec, layout_previo=layout))
		self.assertEqual(regenerado[carril][3], 160.0)

	def test_ruta_valida(self):
		a = (0, 0, 100, 80)
		b = (200, 0, 100, 80)
		self.assertTrue(_ruta_valida([(100, 40), (200, 40)], a, b, [a, b]))
		self.assertFalse(_ruta_valida([(100, 40), (200, 60)], a, b, [a, b]))  # diagonal
		self.assertFalse(_ruta_valida([(50, 40), (200, 40)], a, b, [a, b]))  # sale de dentro


if __name__ == "__main__":
	unittest.main()
