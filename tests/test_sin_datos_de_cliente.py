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


def _fixtures_declarados():
	arbol = ast.parse((APP / "hooks.py").read_text(encoding="utf-8"))
	for nodo in arbol.body:
		if isinstance(nodo, ast.Assign) and any(getattr(t, "id", None) == "fixtures" for t in nodo.targets):
			return ast.literal_eval(nodo.value)
	return []


class TestSinDatosDeCliente(unittest.TestCase):
	def test_no_hay_fixtures_de_datos(self):
		"""Un fixture se importa en CADA sitio en cada migrate: solo valdría para datos universales."""
		self.assertEqual(_fixtures_declarados(), [])
		ficheros = list((APP / "fixtures").glob("*.json")) if (APP / "fixtures").exists() else []
		self.assertEqual([f.name for f in ficheros], [])

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
