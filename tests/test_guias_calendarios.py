"""Guías de arranque, calendarios y altas rápidas: que apunten a lo que existe.

Son tres patrones nativos de Frappe que ERPNext usa en sus módulos (1.7.8):

- **Guía de arranque**: un `Module Onboarding` con sus `Onboarding Step`, mostrado como bloque
  «onboarding» en la portada del área. Frappe la oculta si System Settings no tiene
  `enable_onboarding` (frappe/desk/desktop.py: `get_onboarding_doc`).
- **Calendario y Gantt**: `<doctype>_calendar.js` (frappe/desk/form/meta.py: `__calendar_js`).
- **Alta rápida**: `quick_entry` en el DocType; el diálogo pide los obligatorios y los marcados
  `allow_in_quick_entry`, y Frappe abre el formulario completo si hay más de 7 o alguna tabla
  obligatoria (frappe/public/js/frappe/form/quick_entry.js).

Se comprueba sin Frappe, leyendo los ficheros.
"""

import json
import re
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "sgc"


def _doctypes():
	return {
		json.loads(p.read_text(encoding="utf-8"))["name"]: json.loads(p.read_text(encoding="utf-8"))
		for p in APP.glob("*/doctype/*/*.json")
		if p.parent.name == p.stem
	}


def _slug(nombre):
	return nombre.lower().replace(" ", "-")


class TestGuiasDeArranque(unittest.TestCase):
	def setUp(self):
		self.guias = {
			json.loads(p.read_text(encoding="utf-8"))["name"]: json.loads(p.read_text(encoding="utf-8"))
			for p in APP.glob("*/module_onboarding/*/*.json")
		}
		self.pasos = {
			json.loads(p.read_text(encoding="utf-8"))["name"]: json.loads(p.read_text(encoding="utf-8"))
			for p in APP.glob("*/onboarding_step/*/*.json")
		}
		self.doctypes = _doctypes()
		self.roles = {r["name"] for r in json.loads((APP / "fixtures" / "role.json").read_text(encoding="utf-8"))}

	def test_cada_portada_con_guia_apunta_a_una_guia_que_existe(self):
		usadas = set()
		for ruta in APP.glob("*/workspace/*/*.json"):
			for bloque in json.loads(json.loads(ruta.read_text(encoding="utf-8"))["content"]):
				if bloque["type"] == "onboarding":
					nombre = bloque["data"]["onboarding_name"]
					self.assertIn(nombre, self.guias, ruta.name)
					usadas.add(nombre)
		self.assertEqual(usadas, set(self.guias), "toda guía debe salir en alguna portada")

	def test_los_pasos_existen_y_ninguno_sobra(self):
		referidos = {s["step"] for g in self.guias.values() for s in g["steps"]}
		self.assertEqual(referidos - set(self.pasos), set())
		self.assertEqual(set(self.pasos) - referidos, set())

	def test_la_carpeta_es_la_que_usa_frappe_al_exportar(self):
		for ruta in [*APP.glob("*/module_onboarding/*/*.json"), *APP.glob("*/onboarding_step/*/*.json")]:
			nombre = json.loads(ruta.read_text(encoding="utf-8"))["name"]
			self.assertEqual(ruta.stem, nombre.replace(" ", "_").replace("-", "_").lower(), nombre)

	def test_la_guia_la_ven_roles_del_producto(self):
		for nombre, guia in self.guias.items():
			roles = {r["role"] for r in guia["allow_roles"]}
			self.assertTrue(roles, nombre)
			self.assertEqual(roles - self.roles, set(), nombre)

	def test_cada_paso_apunta_a_un_doctype_o_a_una_pantalla_que_existe(self):
		slugs = {_slug(n) for n in self.doctypes}
		for nombre, paso in self.pasos.items():
			with self.subTest(paso=nombre):
				if paso["action"] == "Create Entry":
					self.assertIn(paso["reference_document"], self.doctypes)
				else:
					self.assertEqual(paso["action"], "Go to Page")
					m = re.match(r"^/desk/([a-z\-]+)(/view/(calendar|gantt))?(\?.*)?$", paso["path"])
					self.assertIsNotNone(m, paso["path"])
					self.assertIn(m.group(1), slugs, paso["path"])
					if m.group(3):
						self.assertTrue((APP.glob(f"*/doctype/{m.group(1).replace('-', '_')}/*_calendar.js")), paso["path"])


class TestCalendarios(unittest.TestCase):
	def test_los_campos_del_calendario_existen_en_el_doctype(self):
		doctypes = _doctypes()
		rutas = sorted(APP.glob("*/doctype/*/*_calendar.js"))
		self.assertGreaterEqual(len(rutas), 6)
		for ruta in rutas:
			js = ruta.read_text(encoding="utf-8")
			doctype = re.search(r'frappe\.views\.calendar\["([^"]+)"\]', js).group(1)
			campos = {f["fieldname"]: f for f in doctypes[doctype]["fields"]}
			with self.subTest(doctype=doctype):
				for clave in ("start", "end", "title", "progress"):
					m = re.search(rf'\b{clave}: "([a-z_]+)"', js)
					if m:
						self.assertIn(m.group(1), campos, f"{clave} → {m.group(1)}")
						if clave in ("start", "end"):
							self.assertIn(campos[m.group(1)]["fieldtype"], ("Date", "Datetime"))
				for m in re.finditer(r'fieldname: "([a-z_]+)"', js):
					self.assertIn(m.group(1), campos, f"filtro → {m.group(1)}")


class TestAltaRapida(unittest.TestCase):
	def test_las_altas_rapidas_caben_en_el_dialogo(self):
		con_alta = {n: d for n, d in _doctypes().items() if d.get("quick_entry")}
		self.assertTrue({"No Conformidad", "Evento Riesgo", "Salida No Conforme"} <= set(con_alta))
		for nombre, doc in con_alta.items():
			campos = [f for f in doc["fields"] if f.get("reqd") or f.get("allow_in_quick_entry")]
			with self.subTest(doctype=nombre):
				self.assertLessEqual(len(campos), 7, "con más de 7 Frappe abre el formulario completo")
				self.assertFalse([f for f in campos if f["fieldtype"] in ("Table", "Table MultiSelect")])
				self.assertNotEqual((doc.get("autoname") or "").lower(), "prompt")


if __name__ == "__main__":
	unittest.main()
