"""Una portada no ofrece «Nuevo X» a quien no puede crear X.

Frappe muestra un atajo de portada a cualquiera que pueda LEER su DocType
(`frappe/desk/desktop.py::get_shortcuts` → `is_item_allowed`), y el atajo con
`doc_view: "New"` abre el alta rápida sin mirar el permiso de crear
(`frappe/public/js/frappe/widgets/shortcut_widget.js`). Quien solo lee lo ve, lo pulsa y
recibe un error. Las portadas son comunes a todos los roles y no se pueden filtrar por rol de
forma nativa, así que un atajo de crear solo vale si lo puede usar cualquier usuario del Desk:
el DocType da `create` a «Desk User» o a «All». Para lo demás, la lista ya trae «+ Agregar»
solo para quien puede crear. Se comprueba sin Frappe, leyendo los JSON.
"""

import json
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "sgc"
TODOS = {"Desk User", "All"}


def _doctype(nombre):
	carpeta = nombre.lower().replace(" ", "_")
	rutas = list(APP.glob(f"*/doctype/{carpeta}/{carpeta}.json"))
	return json.loads(rutas[0].read_text(encoding="utf-8")) if rutas else None


class TestAtajosCrear(unittest.TestCase):
	def test_solo_atajos_de_crear_que_puede_usar_cualquiera(self):
		portadas = sorted(APP.glob("*/workspace/*/*.json"))
		self.assertTrue(portadas)
		for ruta in portadas:
			portada = json.loads(ruta.read_text(encoding="utf-8"))
			for atajo in portada.get("shortcuts", []):
				if atajo.get("type") != "DocType" or atajo.get("doc_view") != "New":
					continue
				with self.subTest(portada=portada["name"], atajo=atajo["label"]):
					doctype = _doctype(atajo["link_to"])
					self.assertIsNotNone(doctype, f"{atajo['link_to']} no es un DocType del SGC")
					crean = {p["role"] for p in doctype["permissions"] if p.get("create")}
					self.assertTrue(
						crean & TODOS,
						f"«{atajo['label']}» en {portada['name']}: lo ve quien lee {atajo['link_to']}, "
						f"pero solo crean {sorted(crean)}. Quítalo o enlaza la lista.",
					)
