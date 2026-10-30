"""Los filtros de lista estándar (`list_filter/*.json`) están bien declarados.

Frappe los sincroniza en cada `migrate` desde `sgc/<módulo>/doctype/<doctype>/list_filter/`
(`frappe/model/sync.py::get_doc_files`) y borra los que se quedan sin fichero
(`remove_orphan_entities`, por el `name` del JSON). Un fallo aquí no se ve hasta que alguien
abre la lista: un campo renombrado o un estado que ya no existe deja el filtro vacío sin avisar,
y Frappe descarta en silencio las condiciones sobre campos que no conoce
(`list_filter.py::_sanitize_filters`). Se comprueba sin Frappe, leyendo los JSON.
"""

import json
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "sgc"
MODULOS = {m.strip() for m in (APP / "modules.txt").read_text(encoding="utf-8").splitlines() if m.strip()}
# frappe/model/__init__.py: std_fields, más el pseudo-campo de estado que acepta list_filter.py
CAMPOS_ESTANDAR = {
	"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx",
	"_user_tags", "_comments", "_assign", "_liked_by", "status_field",
}
TIPOS_FECHA = {"Date", "Datetime"}
COMPARADORES = {"<", "<=", ">", ">="}


def _scrub(texto):
	"""Igual que `frappe.scrub`."""
	return texto.replace(" ", "_").replace("-", "_").lower()


def _firma(referencia, filtros):
	"""Igual que `frappe/desk/doctype/list_filter/list_filter.py::compute_route_signature`."""
	params = []
	for dt, campo, operador, valor in (f[:4] for f in filtros):
		clave = campo if dt == referencia else f"{dt}.{campo}"
		texto = str(valor) if operador == "=" else json.dumps([operador, valor], separators=(",", ":"))
		params.append((clave, texto))
	params.sort(key=lambda p: (p[0], p[1]))
	return "&".join(f"{k}={v}" for k, v in params)


def _filtros_de_lista():
	return sorted(APP.glob("*/doctype/*/list_filter/*.json"))


def _doctype(carpeta):
	ruta = carpeta / f"{carpeta.name}.json"
	return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


class TestListFilters(unittest.TestCase):
	def test_hay_filtros_que_revisar(self):
		self.assertTrue(_filtros_de_lista())

	def test_cada_filtro_esta_bien_declarado(self):
		nombres = set()
		for ruta in _filtros_de_lista():
			rel = ruta.relative_to(APP).as_posix()
			filtro = json.loads(ruta.read_text(encoding="utf-8"))
			carpeta_doctype = ruta.parent.parent
			doctype = _doctype(carpeta_doctype)
			with self.subTest(filtro=rel):
				self.assertEqual(filtro.get("doctype"), "List Filter")
				self.assertEqual(filtro.get("is_standard"), 1, "solo los estándar se sincronizan y se vigilan")
				self.assertFalse(filtro.get("for_user"), "un filtro estándar no puede ser de un usuario")
				self.assertTrue(filtro.get("filter_name"))

				# reference_doctype ↔ carpeta, y el DocType existe en la app
				referencia = filtro.get("reference_doctype") or ""
				self.assertEqual(_scrub(referencia), carpeta_doctype.name)
				self.assertIsNotNone(doctype, f"no hay DocType {referencia} en {carpeta_doctype}")
				self.assertEqual(doctype["name"], referencia)

				# módulo declarado, el del DocType y el de la carpeta donde vive
				modulo = filtro.get("module")
				self.assertIn(modulo, MODULOS)
				self.assertEqual(modulo, doctype["module"])
				self.assertEqual(_scrub(modulo), ruta.relative_to(APP).parts[0])

				# nombre = autoname de Frappe, y el fichero = el que exportaría (`get_export_path`)
				self.assertEqual(filtro.get("name"), f"{referencia}-{filtro['filter_name']}")
				self.assertEqual(ruta.name, f"{_scrub(filtro['name'])}.json")
				self.assertNotIn(filtro["name"], nombres, "nombre de filtro repetido")
				nombres.add(filtro["name"])

	def test_los_filtros_usan_campos_y_valores_que_existen(self):
		for ruta in _filtros_de_lista():
			rel = ruta.relative_to(APP).as_posix()
			filtro = json.loads(ruta.read_text(encoding="utf-8"))
			doctype = _doctype(ruta.parent.parent)
			campos = {f["fieldname"]: f for f in doctype["fields"]}
			condiciones = json.loads(filtro.get("filters") or "[]")
			with self.subTest(filtro=rel):
				self.assertTrue(condiciones, "un filtro sin condiciones es la lista entera")
				self.assertEqual(filtro.get("route_signature"), _firma(filtro["reference_doctype"], condiciones))
				if filtro.get("sort_field"):
					self.assertIn(filtro["sort_field"], set(campos) | CAMPOS_ESTANDAR)
					self.assertIn(filtro.get("sort_order"), ("asc", "desc"))
			for condicion in condiciones:
				with self.subTest(filtro=rel, condicion=condicion):
					self.assertEqual(len(condicion), 4)
					dt, campo, operador, valor = condicion
					self.assertEqual(dt, filtro["reference_doctype"])
					self.assertIn(campo, set(campos) | CAMPOS_ESTANDAR, "Frappe descarta el campo sin avisar")
					definicion = campos.get(campo, {})
					if definicion.get("fieldtype") in TIPOS_FECHA:
						# `campo <= hoy` se traduce a IFNULL(campo, '0001-01-01'): los vacíos cuentan.
						self.assertNotIn(operador, COMPARADORES, "usa Timespan o between")
					if definicion.get("fieldtype") == "Select" and operador in ("=", "!=", "in", "not in"):
						opciones = set((definicion.get("options") or "").split("\n"))
						valores = valor if isinstance(valor, list) else [valor]
						self.assertEqual(sorted(set(valores) - opciones), [], "valor que el campo no tiene")


if __name__ == "__main__":
	unittest.main()
