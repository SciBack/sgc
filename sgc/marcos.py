"""Alcance de un Marco Normativo: qué se evalúa con él.

La normativa peruana mantiene separadas tres cosas que se confunden a diario:
el LICENCIAMIENTO que otorga Sunedu (permiso para operar, obligatorio) y la
ACREDITACIÓN del Sineace/Coneau (sello voluntario de calidad), que además viene
en dos modelos distintos — por programa de estudios y institucional —, con
distinto número de estándares y distinto umbral de excelencia.

No es una distinción académica: el Modelo de Acreditación Institucional del
Coneau (2026, §4.2) explica que sus estándares se definieron revisando las
condiciones básicas de Sunedu «para diferenciar los niveles de exigencia».
Cruzarlos produce resultados que ninguna entidad ha otorgado — comprobado en
producción, donde una autoevaluación abierta con el marco de licenciamiento
llegaba a emitir «Acreditado 6 años».
"""

import frappe

LICENCIAMIENTO = "Licenciamiento"
ACRED_PROGRAMA = "Acreditación de programa"
ACRED_INSTITUCIONAL = "Acreditación institucional"


def alcance_de(marco: str | None) -> str | None:
	"""Alcance declarado del marco, o `None` si no hay marco o no está declarado.

	Devuelve `None` —en vez de reventar— cuando el campo todavía no existe en la
	base. Un sitio a medio migrar debe comportarse como antes de la validación,
	no quedarse inservible: la primera versión de este guard consultaba el campo
	a ciegas y tumbó la suite entera con `column "alcance" does not exist`. Una
	regla de coherencia no puede ser más frágil que lo que protege.
	"""
	if not marco:
		return None
	if not frappe.get_meta("Marco Normativo").has_field("alcance"):
		return None
	return frappe.db.get_value("Marco Normativo", marco, "alcance") or None


def es_de_licenciamiento(marco: str | None) -> bool:
	"""¿Este marco sirve para el permiso de operar (y no para acreditar)?

	Si el alcance no está declarado se cae al `ente`: lo emitido por Sunedu es
	licenciamiento. La duda se resuelve siempre hacia el lado prudente — dar por
	acreditación algo que no lo es sería justo el error que este módulo evita.
	"""
	if not marco:
		return False
	if alcance_de(marco) == LICENCIAMIENTO:
		return True
	return frappe.db.get_value("Marco Normativo", marco, "ente") == "SUNEDU"


def es_de_acreditacion(marco: str | None) -> bool:
	"""¿Este marco acredita (programa o institucional)?

	Aquí NO hay regla de respaldo por `ente`, a diferencia de
	`es_de_licenciamiento`, y la asimetría es deliberada: solo se afirma cuando
	el alcance está declarado.

	El motivo es que los dos errores no cuestan lo mismo. Confundir
	licenciamiento con acreditación **emite un sello que nadie otorgó**, así que
	ahí se bloquea incluso ante la duda. Al revés solo se ensucia un
	diagnóstico, mientras que bloquear de más impide trabajar con cualquier
	marco todavía sin clasificar — que fue justo lo que ocurrió al primer
	intento: dar por acreditación todo lo emitido por el Sineace dejó sin poder
	crear informes a media suite.
	"""
	if not marco:
		return False
	return alcance_de(marco) in (ACRED_PROGRAMA, ACRED_INSTITUCIONAL)
