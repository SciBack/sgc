"""Actividad de los registros relacionados en el timeline del formulario.

En una no conformidad no se veía qué pasaba con sus acciones de mejora ni con el
hallazgo que la originó: había que abrirlos uno por uno. Este módulo junta en el
timeline del registro padre las altas, los cambios de estado y los comentarios de sus
registros relacionados. El patrón viene de Frappe CRM (`crm/api/activities.py`), y se
monta con el hook nativo `additional_timeline_content`
(`frappe/desk/form/load.py::get_additional_timeline_content`), que el Desk pinta en
`form_timeline.js::get_custom_timeline_contents`.

Dos reglas:

- **Permisos.** Los relacionados se buscan con `frappe.get_list`, que aplica los
  permisos y la visibilidad por sede: nadie ve en el timeline un registro que su lista
  le oculta. Los comentarios se leen después, solo de los registros que pasaron ese filtro.
- **Escapar todo.** El Desk inserta `content` como HTML sin filtrar
  (`form_timeline.js`), así que títulos, nombres y comentarios se escapan aquí. No se usa
  `timeline_badge` ni `method`: esa rama del Desk evalúa código (`frappe.utils.eval`).
"""

import html

import frappe
from frappe import _
from frappe.utils import escape_html, get_fullname, get_link_to_form, strip_html

# Registro padre → (DocType relacionado, campo Link que apunta al padre).
RELACIONADOS = {
	"No Conformidad": (
		("Accion Mejora", "no_conformidad"),
		("Hallazgo", "no_conformidad"),
		("Hallazgo Auditoria", "no_conformidad"),
		("Salida No Conforme", "no_conformidad"),
		("Evento Riesgo", "no_conformidad"),
		("Entrega Obligacion", "no_conformidad"),
	),
	"Plan Mejora": (
		("Accion Mejora", "plan_mejora"),
		("No Conformidad", "plan_mejora"),
	),
	"Auditoria": (
		("Hallazgo Auditoria", "auditoria"),
		("Lista Verificacion", "auditoria"),
		("Informe Auditoria", "auditoria"),
	),
}

# Entradas como máximo, las más recientes. El timeline se carga cada vez que se abre el formulario.
LIMITE = 50
# Caracteres de un comentario que se citan en el timeline.
LARGO_CITA = 200


def timeline(doctype, docname):
	"""Entradas para `additional_timeline_content`: lista de `{icon, creation, content}`."""
	entradas = []
	for relacionado, campo in RELACIONADOS.get(doctype, ()):
		if frappe.has_permission(relacionado, "read"):
			entradas.extend(_actividad(relacionado, campo, docname))
	entradas.sort(key=lambda e: e["creation"], reverse=True)
	return entradas[:LIMITE]


def _actividad(relacionado, campo, docname):
	titulo = frappe.get_meta(relacionado).title_field
	campos = ["name", "owner", "creation"] + ([titulo] if titulo and titulo != "name" else [])
	filas = frappe.get_list(
		relacionado, filters={campo: docname}, fields=campos, order_by="creation desc", limit=LIMITE
	)
	if not filas:
		return []

	tipo = escape_html(_(relacionado))
	enlaces = {}
	for fila in filas:
		# Varios DocTypes usan como título el propio código: no repetirlo.
		valor = fila.get(titulo) if titulo else None
		texto = f"{fila.name} · {valor}" if valor and valor != fila.name else fila.name
		enlaces[fila.name] = get_link_to_form(relacionado, fila.name, escape_html(texto))

	entradas = [
		_entrada("es-line-add", fila.creation, _("{0} creó {1} {2}").format(_persona(fila.owner), tipo, enlaces[fila.name]))
		for fila in filas
	]

	comentarios = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": relacionado,
			"reference_name": ["in", list(enlaces)],
			"comment_type": ["in", ["Workflow", "Comment"]],
		},
		fields=["reference_name", "comment_type", "content", "owner", "creation"],
		order_by="creation desc",
		limit=LIMITE,
	)
	for c in comentarios:
		texto = _texto_plano(c.content)
		if c.comment_type == "Workflow":
			contenido = _("{0} pasó {1} {2} a «{3}»").format(
				_persona(c.owner), tipo, enlaces[c.reference_name], escape_html(texto))
			entradas.append(_entrada("branch", c.creation, contenido))
		else:
			if len(texto) > LARGO_CITA:
				texto = texto[:LARGO_CITA].rstrip() + "…"
			contenido = _("{0} comentó en {1} {2}: «{3}»").format(
				_persona(c.owner), tipo, enlaces[c.reference_name], escape_html(texto))
			entradas.append(_entrada("es-line-chat-alt", c.creation, contenido))
	return entradas


def _entrada(icono, creation, contenido):
	return {"icon": icono, "creation": creation, "content": contenido}


def _texto_plano(contenido):
	"""El comentario como texto: sin etiquetas y con las entidades ya decodificadas.

	El editor del Desk guarda HTML con entidades (`5 &lt; 7`). Se decodifican antes de
	escapar para no mostrar `&amp;lt;`, y antes de recortar para no partir una entidad.
	"""
	return html.unescape(strip_html(contenido or "")).strip()


def _persona(usuario):
	return f"<b>{escape_html(get_fullname(usuario))}</b>"
