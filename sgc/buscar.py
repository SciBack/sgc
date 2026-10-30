# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Buscar enlaces sin pelearse con las tildes.

En castellano casi todo lleva tilde, y la búsqueda de Frappe compara el texto
tal cual: `LIKE '%gestion%'` no encuentra «Gestión». Comprobado en producción el
2026-08-24 sobre los 22 procesos:

    buscar «gestion»   ->  0 resultados
    buscar «gestión»   -> 10
    quitando las tildes de ambos lados -> 14

Y el efecto es peor de lo que parece, porque quien busca no sabe que el problema
es la tilde: escribe «tecnolog», no encuentra «Gestión tecnológica» —la `ó` corta
la coincidencia— y concluye que el buscador no funciona. La persona que lo probó
llegó a intentar teclear la tilde a mano para que apareciera.

**Es una link query estándar de Frappe**, registrada en `standard_queries`
(hooks.py): misma firma que las suyas, y usa `get_match_cond` para respetar los
permisos por fila igual que ellas. No se inventa un endpoint aparte.

Lo único propio es normalizar los dos lados con `translate` antes de comparar.
No hace falta la extensión `unaccent` de PostgreSQL —que exige superusuario y no
está instalada— y cubre lo que se usa en castellano.
"""

import frappe
from frappe.desk.reportview import get_filters_cond, get_match_cond

# Las vocales acentuadas del castellano más la diéresis y la eñe. La `ñ` se
# normaliza a `n` a propósito: quien escribe «diseno» buscando «diseño» merece
# encontrarlo igual que quien escribe «gestion».
ACENTOS = "áéíóúÁÉÍÓÚüÜñÑàèìòùÀÈÌÒÙ"
LLANAS = "aeiouAEIOUuUnNaeiouAEIOU"


def _sin_tildes(expresion: str) -> str:
	"""SQL que devuelve la expresión en minúsculas y sin tildes."""
	return f"translate(lower({expresion}), '{ACENTOS}', '{LLANAS}')"


@frappe.whitelist()
def enlaces(doctype, txt, searchfield, start, page_len, filters, as_dict=False):
	"""Link query insensible a tildes, mayúsculas y posición.

	Busca en el `name` y en el campo de título del DocType. Devuelve la tupla
	(name, título) que espera el buscador de Frappe, o diccionarios si lo pide con
	`as_dict` (el diálogo «Obtener de…», `MultiSelectDialog`, lo hace: sin aceptar el
	argumento, `frappe.call` lo descarta y el diálogo recibe tuplas que no sabe pintar).
	"""
	meta = frappe.get_meta(doctype)
	titulo = meta.title_field if meta.title_field else "name"

	texto = _sin_tildes("%(txt)s")
	condiciones = [f"{_sin_tildes('`tab' + doctype + '`.name')} like {texto}"]
	campos = ["`tab{0}`.name".format(doctype)]

	if titulo != "name":
		condiciones.append(f"{_sin_tildes(f'`tab{doctype}`.`{titulo}`')} like {texto}")
		campos.append(f"`tab{doctype}`.`{titulo}`")

	# Los filtros del desplegable (`set_query`, `link_filters`) llegan aquí y hay que
	# aplicarlos: una standard_query que los ignora anula todos los filtros de los
	# DocTypes que la usan (pasó con la sede de una unidad: 64 opciones en vez de 3).
	# Mismo patrón que las consultas de ERPNext (`erpnext/controllers/queries.py`).
	# Los `%` se doblan porque la consulta lleva parámetros `%(txt)s`.
	filtros = get_filters_cond(doctype, filters, []).replace("%", "%%")

	# `limit n offset m`, no `limit m, n`: eso último es sintaxis de MySQL y
	# PostgreSQL la rechaza. Y sin `locate()` para priorizar coincidencias al
	# principio, porque el traductor de Frappe a PostgreSQL la convierte mal
	# —mete el segundo argumento dentro de `lower()`— y rompe la consulta.
	# Comprobado en producción el 2026-08-24. Se ordena por el título, que para
	# un desplegable de búsqueda es suficiente y no miente.
	return frappe.db.sql(
		"""
		select {campos}
		from `tab{doctype}`
		where ({condiciones})
			{filtros}
			{match}
		order by {orden}
		limit %(page_len)s offset %(start)s
		""".format(
			campos=", ".join(campos),
			doctype=doctype,
			condiciones=" or ".join(condiciones),
			filtros=filtros,
			match=get_match_cond(doctype),
			orden=f"`tab{doctype}`.`{titulo}`" if titulo != "name" else f"`tab{doctype}`.name",
		),
		{
			"txt": f"%{txt or ''}%",
			"start": frappe.utils.cint(start),
			"page_len": frappe.utils.cint(page_len),
		},
		as_dict=frappe.utils.cint(as_dict),
	)
