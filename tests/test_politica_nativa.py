"""La política «el SGC se construye con lo que Frappe trae» (docs/desarrollo/nativo-frappe.md).

Sin Frappe: se lee el código. Cada lista de abajo es la deuda que se acepta HOY; ampliarla
exige cambiar este fichero y la política en el mismo PR, con el motivo. Reducirla es libre.
"""

import ast
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "sgc"

OVERRIDE_CLASES = {"File"}
OVERRIDE_METODOS = {
	"frappe.core.api.file.zip_files",
	"frappe.core.doctype.user.user.update_password",
	"frappe.core.doctype.user.user.test_password_strength",
}
JS_GLOBAL = {"/assets/sgc/js/latido_scheduler.js", "/assets/sgc/js/soporte.js"}
CSS_GLOBAL: set = set()
TRAS_MIGRAR = {"sgc.setup.f_deploy_run_all.run"}

# La configuración que Frappe sincroniza sola y que, por tanto, ningún código debe crear.
CONFIGURACION = (
	"Workspace", "Workflow", "Workflow State", "Workflow Action Master", "Notification",
	"Print Format", "Role", "Role Profile", "Custom DocPerm", "Number Card", "Dashboard Chart",
	"Sidebar", "Workspace Sidebar", "Custom Field", "Property Setter",
)
BLOQUES_NATIVOS = {"header", "paragraph", "shortcut", "quick_list", "number_card", "chart", "card", "spacer"}


def _hooks():
	"""Asignaciones de nivel de módulo de hooks.py que sean literales."""
	valores = {}
	for nodo in ast.parse((APP / "hooks.py").read_text(encoding="utf-8")).body:
		if isinstance(nodo, ast.Assign):
			try:
				valor = ast.literal_eval(nodo.value)
			except (ValueError, SyntaxError, TypeError):
				continue
			for destino in nodo.targets:
				if isinstance(destino, ast.Name):
					valores[destino.id] = valor
	return valores


def _como_conjunto(valor):
	if not valor:
		return set()
	return {valor} if isinstance(valor, str) else set(valor)


class TestPoliticaNativa(unittest.TestCase):
	def setUp(self):
		self.hooks = _hooks()

	def test_sin_sobrescrituras_nuevas_de_frappe(self):
		self.assertEqual(set(self.hooks.get("override_doctype_class", {})) - OVERRIDE_CLASES, set())
		self.assertEqual(set(self.hooks.get("override_whitelisted_methods", {})) - OVERRIDE_METODOS, set())

	def test_sin_js_ni_css_global_nuevo(self):
		self.assertEqual(_como_conjunto(self.hooks.get("app_include_js")) - JS_GLOBAL, set())
		self.assertEqual(_como_conjunto(self.hooks.get("app_include_css")) - CSS_GLOBAL, set())

	def test_tras_migrar_solo_corre_lo_de_cada_institucion(self):
		self.assertEqual(_como_conjunto(self.hooks.get("after_migrate")) - TRAS_MIGRAR, set())

	def test_el_codigo_no_crea_configuracion(self):
		patron = re.compile(r"""["']doctype["']\s*:\s*["'](%s)["']""" % "|".join(map(re.escape, CONFIGURACION)))
		hallados = []
		for ruta in APP.rglob("*.py"):
			rel = ruta.relative_to(APP).as_posix()
			if "/tests/" in f"/{rel}" or rel.split("/")[-1].startswith("test_") or rel.startswith("patches/"):
				continue
			for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
				if patron.search(linea):
					hallados.append(f"{rel}:{n}: {linea.strip()}")
		self.assertEqual(hallados, [], "configuración creada por código: va como fichero estándar o fixture")

	def test_las_portadas_solo_usan_bloques_nativos(self):
		for ruta in sorted(APP.glob("*/workspace/*/*.json")):
			portada = json.loads(ruta.read_text(encoding="utf-8"))
			tipos = {b["type"] for b in json.loads(portada["content"])}
			with self.subTest(portada=portada["name"]):
				self.assertEqual(tipos - BLOQUES_NATIVOS, set())


	def test_esperan_mi_decision_filtra_estados_que_existen(self):
		"""La bandeja de decisiones filtra Workflow Action por estado: un estado renombrado la vaciaría sin avisar."""
		estados = {s["state"] for w in json.loads((APP / "fixtures" / "workflow.json").read_text(encoding="utf-8"))
				   for s in w["states"]}
		portada = json.loads((APP / "sgc_nucleo" / "workspace" / "sgc" / "sgc.json").read_text(encoding="utf-8"))
		lista = next(q for q in portada["quick_lists"] if q["document_type"] == "Workflow Action")
		filtrados = json.loads(re.search(r'"in",(\[.*?\])\]', lista["quick_list_filter"]).group(1))
		self.assertTrue(filtrados)
		self.assertEqual(sorted(set(filtrados) - estados), [])
		atajo = next(s for s in portada["shortcuts"] if s["link_to"] == "Workflow Action")
		self.assertEqual(atajo["stats_filter"], lista["quick_list_filter"])


if __name__ == "__main__":
	unittest.main()
