"""Ningún filtro de portada compara una fecha con «hoy» usando `<`, `<=`, `>` o `>=`.

Frappe traduce `campo <= hoy` a `IFNULL(campo, '0001-01-01') <= hoy`, así que los registros SIN
fecha cuentan como vencidos o pendientes. Pasó con «Por medir»: las 94 fichas de indicador sin
próxima medición salían todas como pendientes. Se usa `between` desde 1900, que excluye los vacíos
(la misma regla que sigue `sgc/dashboards.py`). Se comprueba sin Frappe, leyendo los JSON.
"""

import json
import re
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "sgc"
COMPARADOR_CON_HOY = re.compile(r'"(<|<=|>|>=)"\s*,\s*frappe\.datetime\.')


def _filtros_de_portada():
	for fichero in sorted(APP.glob("*/workspace/*/*.json")):
		datos = json.loads(fichero.read_text(encoding="utf-8"))
		for atajo in datos.get("shortcuts", []):
			if atajo.get("stats_filter"):
				yield fichero, atajo.get("label"), atajo["stats_filter"]


class TestFiltrosFecha(unittest.TestCase):
	def test_hay_filtros_que_revisar(self):
		self.assertTrue(list(_filtros_de_portada()))

	def test_ningun_filtro_compara_una_fecha_con_hoy(self):
		malos = [
			f"{fichero.relative_to(APP)} · {etiqueta}"
			for fichero, etiqueta, filtro in _filtros_de_portada()
			if COMPARADOR_CON_HOY.search(filtro)
		]
		self.assertEqual(malos, [], "Usa between ['1900-01-01', hoy]: los vacíos cuentan como vencidos")


if __name__ == "__main__":
	unittest.main()
