"""Lo que el SGC trae para cualquier institución, tal como lo trae: documentos estándar de Frappe.

Desde la 1.2.0 nada de esto lo construye un script en cada `migrate`:

- **Roles, perfiles de rol, workflows con sus estados y acciones**: fixtures (`sgc/fixtures/`),
  declarados en `hooks.fixtures` e importados por Frappe en cada `migrate`.
- **Permisos**: los estándar de cada DocType del SGC (su JSON). Lo que una institución cambie
  en el Role Permission Manager queda como Custom DocPerm, aparte, y sobrevive a las
  actualizaciones.
- **Avisos** (Notification) y **formatos de impresión** (Print Format): estándar, en la carpeta
  de su módulo.

Este módulo solo LEE esos ficheros: lo usan la verificación de instancia y las pruebas. Para
cambiar algo, se cambia el fichero (o se edita en un sitio con `developer_mode` y Frappe lo
exporta). El Desk (portadas y menús) lo lee `sgc/escritorio.py`.
"""

import json
from functools import cache
from pathlib import Path

import frappe

APP = "sgc"


def _raiz():
	return Path(frappe.get_app_path(APP))


def _leer(ruta):
	return json.loads(Path(ruta).read_text(encoding="utf-8"))


def fixture(nombre):
	"""Los registros de `sgc/fixtures/<nombre>.json` (p. ej. «workflow», «role»)."""
	ruta = _raiz() / "fixtures" / f"{nombre}.json"
	return _leer(ruta) if ruta.exists() else []


def roles():
	"""{rol: registro} — el catálogo de roles del SGC, con su `desk_access`."""
	return {r["name"]: r for r in fixture("role")}


def perfiles():
	return {r["name"]: r for r in fixture("role_profile")}


def workflows():
	"""{nombre: workflow}."""
	return {w["name"]: w for w in fixture("workflow")}


def workflow_de(doctype):
	return next((w for w in workflows().values() if w["document_type"] == doctype), None)


def avisos():
	"""{nombre: Notification} — los avisos estándar del SGC."""
	return {d["name"]: d for d in (_leer(r) for r in sorted(_raiz().glob("*/notification/*/*.json")))}


def formatos():
	"""{nombre: Print Format} — los formatos de impresión estándar del SGC."""
	return {d["name"]: d for d in (_leer(r) for r in sorted(_raiz().glob("*/print_format/*/*.json")))}


@cache
def _doctypes():
	return {d["name"]: d for d in (_leer(r) for r in sorted(_raiz().glob("*/doctype/*/*.json")))}


def permisos():
	"""{DocType: [permisos estándar]} de los DocType del SGC que dan permisos a roles del SGC."""
	del_sgc = set(roles())
	return {
		nombre: d["permissions"]
		for nombre, d in _doctypes().items()
		if not d.get("istable") and any(p.get("role") in del_sgc for p in d.get("permissions", []))
	}


def doctypes_con_informe():
	"""Los DocType donde algún rol del SGC tiene «report» (los informes lo exigen sobre su ref_doctype)."""
	del_sgc = set(roles())
	return sorted(dt for dt, filas in permisos().items() if any(p.get("report") and p.get("role") in del_sgc for p in filas))


def roles_efectivos(doctype):
	"""Los roles con permisos sobre un DocType en ESTE sitio.

	Frappe aplica los Custom DocPerm si el DocType tiene alguno y, si no, los estándar.
	"""
	custom = frappe.get_all("Custom DocPerm", filters={"parent": doctype}, pluck="role")
	if custom:
		return set(custom)
	return set(frappe.get_all("DocPerm", filters={"parent": doctype, "parenttype": "DocType"}, pluck="role"))
