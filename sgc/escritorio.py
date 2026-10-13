"""El Desk del SGC tal como lo trae la app: ficheros estándar de Frappe, sin código que lo construya.

Desde la 1.1.0 las portadas (`Workspace`), los menús de cada área (`Sidebar`), las cifras
(`Number Card`) y los gráficos (`Dashboard Chart`) son documentos estándar guardados en la
carpeta de su módulo (`sgc/<módulo>/<tipo>/<nombre>/<nombre>.json`). Frappe los sincroniza en
cada `migrate` y guarda aparte lo que cada sitio personalice, así que una actualización de
Frappe no los pisa ni los rompe. Hasta la 1.0.1 los creaban los pasos f18 y f21 en cada
migrate, y Frappe 16.50 cambió el modelo de menús por debajo de ellos.

Para cambiar el Desk: editar el fichero, o editar en un sitio con `developer_mode` y dejar que
Frappe lo exporte. Este módulo solo LEE esos ficheros (lo usan las pruebas y la verificación).
"""

import json
from pathlib import Path

import frappe

APP = "sgc"
INICIO = "SGC"  # la portada general; el resto de portadas se llaman como su módulo


def _ficheros(carpeta):
	raiz = Path(frappe.get_app_path(APP))
	for ruta in sorted(raiz.glob(f"*/{carpeta}/*/*.json")):
		yield json.loads(ruta.read_text(encoding="utf-8"))


def menus():
	"""{módulo: Sidebar} — un menú por área."""
	return {d["module"]: d for d in _ficheros("sidebar")}


def portadas():
	"""{nombre: Workspace} — la general y una por área."""
	return {d["name"]: d for d in _ficheros("workspace")}


def cifras():
	return list(_ficheros("number_card"))


def graficos():
	return list(_ficheros("dashboard_chart"))


def areas():
	"""{módulo: nombre visible del área}, en el orden de las portadas."""
	por_modulo = menus()
	orden = sorted(portadas().values(), key=lambda w: w.get("sequence_id") or 0)
	return {w["module"]: por_modulo[w["module"]]["title"] for w in orden if w["name"] in por_modulo}


def destinos(menu):
	"""[(etiqueta, tipo, destino)] de los enlaces de un menú."""
	return [(i["label"], i["link_type"], i["link_to"]) for i in menu.get("items", []) if i.get("type") == "Link"]
