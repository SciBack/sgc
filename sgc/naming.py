"""Correlativos que cuentan lo que dicen contar.

Frappe tiene una trampa en el `autoname` de tipo `format:`. Su
`_format_autoname` resuelve **cada `{parámetro}` por separado**, así que el
bloque `{#####}` acaba llamando a `getseries("", 5)`: la serie de nombre
VACÍO. El resultado es un contador GLOBAL del sitio compartido por todos los
DocTypes que usan ese patrón.

Se veía en producción sin necesidad de leer el framework — los códigos salían
consecutivos entre tipos distintos:

    APL-2026-00030 · RES-2026-00031 · RSK-2026-00034 · NC-2026-00035

Es decir, `NC-2026-00035` no significaba «la no conformidad 35 del año», sino
«el documento 35 del sistema». Para quien lee esos códigos —y Calidad los va a
leer— eso es sencillamente información falsa.

Aquí el correlativo se pide con el prefijo YA resuelto (`NC-2026-`), que es lo
que Frappe hace bien cuando el naming va por `naming_series` con puntos. Se usa
`getseries`, el mismo mecanismo del framework: una fila por prefijo en
`tabSeries`, con `for update`, así que es atómico y no hay carreras entre dos
usuarios creando a la vez.

Se engancha por `doc_events` en `hooks.py`, no reescribiendo once
controladores: `set_new_name` ejecuta `doc.run_method("autoname")` ANTES de
mirar el `autoname` del DocType, y respeta el nombre que se haya asignado ahí.
El patrón del DocType se conserva intacto y sigue siendo la fuente de la forma
del código: esto solo cambia de dónde sale el número.
"""

import re

import frappe
from frappe.model.naming import getseries, parse_naming_series
from frappe.utils import cint

_PARAMETRO = re.compile(r"\{[^}]*\}")
_MARCA = "\x00"


def correlativo_por_prefijo(doc, method=None):
	"""Nombra el documento con un correlativo propio de su prefijo.

	No hace nada si el DocType no se autonombra con `format:` o si su patrón no
	lleva bloque de `#` — esos casos ya son correctos y no hay que tocarlos.
	"""
	meta = frappe.get_meta(doc.doctype)
	autoname = meta.autoname or ""
	if not autoname.lower().startswith("format:") or "#" not in autoname:
		return

	plantilla = autoname[autoname.find(":") + 1 :]
	digitos = 0

	def resolver(match):
		nonlocal digitos
		cuerpo = match.group()[1:-1]
		if cuerpo and set(cuerpo) == {"#"}:
			digitos = len(cuerpo)
			return _MARCA
		# El resto de parámetros se resuelven como los resuelve Frappe: puede
		# ser una fecha ({YYYY}) o un campo del propio documento ({anio}).
		return parse_naming_series([cuerpo], doc=doc)

	resuelto = _PARAMETRO.sub(resolver, plantilla)
	if _MARCA not in resuelto:
		return

	prefijo, sufijo = resuelto.split(_MARCA, 1)
	_sembrar_serie(doc.doctype, prefijo, digitos)
	doc.name = prefijo + getseries(prefijo, digitos) + sufijo


def siguiente_correlativo(nombres) -> int:
	"""Máximo sufijo numérico de una lista de códigos + 1.

	La usan los DocTypes que se autonombran por `field:codigo` y componen ese
	código a mano (documento controlado, programa/informe/hallazgo de
	auditoría). Vivía copiada literalmente en los cuatro controladores.

	**Semántica distinta a la de `correlativo_por_prefijo`, y a propósito.**
	Aquí el número sale de mirar los códigos que existen AHORA, así que es
	robusto a borrados: si se elimina el último documento, su número se vuelve a
	usar. Eso es lo que quiere un código que la gente teclea y busca — no deja
	huecos —, y hay un test que lo fija (`test_correlativo_robusto_a_borrados`).
	El contador de `tabSeries`, en cambio, nunca reutiliza: para un identificador
	de sistema es lo correcto, porque un número que reaparece tras un borrado
	puede colisionar con referencias externas ya emitidas.

	Su límite es el reverso de esa virtud: dos inserciones simultáneas leen el
	mismo máximo y proponen el mismo número. Con documentos que se crean a mano
	es teórico, y el `unique` del campo lo convertiría en un error visible, no
	en un duplicado silencioso.
	"""
	maximo = 0
	for n in nombres:
		m = re.search(r"(\d+)$", n or "")
		if m:
			maximo = max(maximo, int(m.group(1)))
	return maximo + 1


def _sembrar_serie(doctype, prefijo, digitos):
	"""Arranca la serie por encima de lo que ya exista con ese prefijo.

	Sin esto, un sitio que ya tenga documentos numerados con el contador global
	viejo (`NC-2026-00035`) empezaría de nuevo en 1 y chocaría en cuanto la
	cuenta alcanzara los nombres existentes. Solo actúa la primera vez: si la
	serie ya está creada, manda ella.
	"""
	if frappe.db.exists("Series", prefijo):
		return

	nombres = frappe.db.sql(
		"select name from `tab{0}` where name like %s".format(doctype),  # nosec
		prefijo + "%",
		pluck=True,
	)
	mayor = 0
	for nombre in nombres:
		cola = nombre[len(prefijo) :]
		cifras = re.match(r"\d+", cola)
		if cifras:
			mayor = max(mayor, cint(cifras.group()))
	if mayor:
		frappe.db.sql(
			"insert into `tabSeries` (name, current) values (%s, %s)", (prefijo, mayor)
		)
