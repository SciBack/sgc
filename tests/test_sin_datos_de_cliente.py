"""Un sitio recién instalado no trae datos, URIs ni opciones de una institución concreta (#102).

El canónico es el producto: lo que instala tiene que valer para cualquier universidad. Lo de
una institución (su tesauro, sus sedes, su identidad) vive en su capa y se carga allí. Aquí se
comprueba, sin Frappe, en lo que llega al sitio por instalación: los fixtures, las definiciones
de pantallas e informes (opciones, valores por defecto, descripciones) y los datos del setup.
"""

import ast
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "sgc"

# Rastros de una institución concreta. Si el canónico necesitara nombrar otra, va aquí.
MARCAS = re.compile(r"upeu|universidad peruana uni[oó]n|juliaca|tarapoto", re.IGNORECASE)


# Lo único que puede viajar como fixture: configuración del producto, igual en todo sitio.
FIXTURES_DE_CONFIGURACION = {
	"Role", "Role Profile", "Workflow", "Workflow State", "Workflow Action Master", "Custom DocPerm",
}


def _fixtures_declarados():
	"""Lee `fixtures` de hooks.py sin Frappe, sustituyendo las constantes de módulo que use."""
	arbol = ast.parse((APP / "hooks.py").read_text(encoding="utf-8"))
	constantes = {}

	class _Sustituir(ast.NodeTransformer):
		def visit_Name(self, nodo):
			if nodo.id in constantes:
				return ast.parse(repr(constantes[nodo.id]), mode="eval").body
			return nodo

	for nodo in arbol.body:
		if not isinstance(nodo, ast.Assign):
			continue
		try:
			valor = ast.literal_eval(_Sustituir().visit(nodo.value))
		except (ValueError, SyntaxError, TypeError):
			continue
		for destino in nodo.targets:
			if getattr(destino, "id", None) == "fixtures":
				return valor
			if isinstance(destino, ast.Name):
				constantes[destino.id] = valor
	return []


class TestSinDatosDeCliente(unittest.TestCase):
	def test_no_hay_fixtures_de_datos(self):
		"""Un fixture se importa en CADA sitio en cada migrate: solo vale para configuración universal."""
		declarados = _fixtures_declarados()
		self.assertTrue(declarados, "hooks.py declara los fixtures de configuración")
		tipos = {f["dt"] if isinstance(f, dict) else f for f in declarados}
		self.assertEqual(tipos - FIXTURES_DE_CONFIGURACION, set())
		esperados = {re.sub(r"[^a-z]+", "_", t.lower()).strip("_") + ".json" for t in tipos}
		ficheros = {f.name for f in (APP / "fixtures").glob("*.json")}
		self.assertEqual(ficheros - esperados, set(), "un fichero en fixtures/ que hooks.py no declara")

	def test_los_fixtures_no_nombran_a_una_institucion(self):
		for ruta in sorted((APP / "fixtures").glob("*.json")):
			with self.subTest(fixture=ruta.name):
				self.assertIsNone(MARCAS.search(ruta.read_text(encoding="utf-8")))

	def test_las_pantallas_e_informes_no_nombran_a_una_institucion(self):
		hallazgos = []
		for ruta in sorted(APP.glob("sgc_*/*/*/*.json")):
			if ruta.stem != ruta.parent.name:
				continue
			d = json.loads(ruta.read_text(encoding="utf-8"))
			if d.get("doctype") not in ("DocType", "Report"):
				continue
			textos = [("descripción", d.get("description") or "")]
			for campo in d.get("fields", []):
				for clave in ("options", "default", "description", "label"):
					textos.append((f"{campo.get('fieldname')}.{clave}", str(campo.get(clave) or "")))
			for donde, texto in textos:
				if MARCAS.search(texto):
					hallazgos.append(f"{d['name']} · {donde}: {texto[:80]}")
		self.assertEqual(hallazgos, [])

	def test_los_datos_del_setup_no_nombran_a_una_institucion(self):
		hallazgos = [
			f"{ruta.name}:{n}: {linea.strip()[:80]}"
			for ruta in sorted((APP / "setup").glob("*.yaml"))
			for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1)
			if MARCAS.search(linea)
		]
		self.assertEqual(hallazgos, [])

	def test_el_sso_no_apunta_a_ninguna_institucion(self):
		"""#46: el issuer, el realm y el host del proveedor salen de site_config, no del código."""
		hallazgos = [
			f"{ruta.name}:{n}: {linea.strip()[:80]}"
			for ruta in (APP / "setup" / "f3b_sso.py", APP / "setup" / "F3B-SSO-DEPLOY.md")
			for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1)
			if MARCAS.search(linea) or re.search(r"https://(?!<|idp\.example\.org|https)[a-z0-9.-]+\.(pe|edu|com|org)\b", linea)
		]
		self.assertEqual(hallazgos, [])


if __name__ == "__main__":
	unittest.main()
