"""Cada estado de flujo tiene un color que dice cómo va el registro.

Frappe pinta el estado según el `style` del Workflow State (frappe/public/js/frappe/model/
indicator.js): Success verde, Warning naranja, Danger rojo, Info celeste, sin estilo gris. Hasta la
1.7.6 los 50 estados eran «Primary» y todo salía azul. Se comprueba sin Frappe, en el fixture.
"""

import json
import unittest
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "sgc" / "fixtures" / "workflow_state.json"
ESTILOS = {"", "Info", "Warning", "Success", "Danger"}


class TestEstadosColor(unittest.TestCase):
	def setUp(self):
		self.estilos = {d["name"]: d.get("style", "") for d in json.loads(FIXTURE.read_text(encoding="utf-8"))}

	def test_ningun_estado_queda_en_el_azul_por_defecto(self):
		self.assertEqual(sorted(n for n, e in self.estilos.items() if e not in ESTILOS), [])

	def test_lo_que_termina_mal_va_en_rojo(self):
		for nombre, estilo in self.estilos.items():
			if "no eficaz" in nombre or nombre == "Materializado":
				self.assertEqual(estilo, "Danger", nombre)

	def test_lo_que_termina_bien_va_en_verde(self):
		for nombre, estilo in self.estilos.items():
			if (nombre.endswith(" eficaz") and "no eficaz" not in nombre) or nombre in ("Publicado", "Aprobado"):
				self.assertEqual(estilo, "Success", nombre)

	def test_lo_que_espera_revision_va_en_naranja(self):
		for nombre, estilo in self.estilos.items():
			if nombre.startswith("En revisi") or nombre.startswith("Observad"):
				self.assertEqual(estilo, "Warning", nombre)


if __name__ == "__main__":
	unittest.main()
