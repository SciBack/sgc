"""El menú Ayuda del Desk lleva al manual de usuario, y a la misma ruta que protege la sesión.

El enlace es un `standard_help_items` de tipo Route (nativo de Frappe). Se comprueba sin
Frappe: que existe, que va a la ruta a la que `sgc.manual_auth` devuelve tras el login, y que
es una ruta del propio sitio fuera del Desk (Frappe la abre en la misma pestaña).
"""

import ast
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

APP = Path(__file__).resolve().parents[1] / "sgc"


def _constante(fichero, nombre):
	arbol = ast.parse((APP / fichero).read_text(encoding="utf-8"))
	for nodo in arbol.body:
		if isinstance(nodo, ast.Assign) and any(getattr(t, "id", None) == nombre for t in nodo.targets):
			return ast.literal_eval(nodo.value)
	raise AssertionError(f"{nombre} no está en {fichero}")


class TestMenuAyuda(unittest.TestCase):
	def setUp(self):
		items = _constante("hooks.py", "standard_help_items")
		self.manual = next((i for i in items if i["item_label"] == "Manual de usuario"), None)

	def test_el_menu_lleva_al_manual(self):
		self.assertIsNotNone(self.manual, "Falta «Manual de usuario» en standard_help_items")
		self.assertEqual(self.manual["item_type"], "Route")
		self.assertEqual(self.manual["is_standard"], 1)

	def test_la_ruta_es_la_que_protege_la_sesion(self):
		destino = parse_qs(urlparse(_constante("manual_auth.py", "LOGIN_LOCATION")).query)["redirect-to"][0]
		self.assertEqual(self.manual["route"], destino)

	def test_es_una_ruta_del_sitio_fuera_del_desk(self):
		ruta = self.manual["route"]
		self.assertTrue(ruta.startswith("/"))
		self.assertFalse(ruta.startswith("/desk"))


if __name__ == "__main__":
	unittest.main()
