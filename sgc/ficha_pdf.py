# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Pregeneración del PDF de la ficha de caracterización.

El portal público sirve este PDF; **no lo renderiza al pedirlo**. El motor de
impresión es Chrome (`pdf_generator="chrome"`), así que renderizar bajo demanda en
un dominio sin login ni límite de peticiones convierte cada descarga en un proceso
de Chrome: mil peticiones seguidas tumban el servidor sin necesitar credenciales.
Por eso el PDF se hace UNA vez, cuando la ficha pasa a `Publicado`, y la vitrina
sirve un fichero ya escrito.

Dos decisiones que el consumidor necesita dar por ciertas:

1. **Nombre estable y con prefijo propio** (`ficha-<name>.pdf`). Sin él, «el .pdf
   más reciente adjunto al documento» sirve cualquier anexo que alguien suba.
2. **Se REEMPLAZA, no se acumula.** Republicar no deja un segundo PDF. Además de
   limpieza, es seguridad: los adjuntos de Frappe se sirven comprobando el permiso
   del DOCTYPE, no el estado del documento, así que un PDF de una versión anterior
   que quedara acumulado seguiría siendo descargable aunque esa versión ya no esté
   vigente. Un solo fichero por ficha es la única forma de que retirar la
   publicación retire de verdad el contenido.
"""
import os
import re

import frappe
from frappe import _

# ⚠️ La variante PÚBLICA, no la institucional. La interna imprime los `full_name`
# de quienes elaboran, revisan y aprueban; este PDF lo sirve una web abierta, y
# esos nombres son datos personales (Ley 29733). La lista blanca de campos del
# portal no bastaba: el dato salía por el PDF. Verificado en el lab el 13-sep-2026.
PRINT_FORMAT = "Ficha de Caracterizacion (publico)"
DOCTYPE = "Ficha Caracterizacion Proceso"
ESTADO_PUBLICO = "Publicado"

# Frappe puede añadir `content_hash[-6:]` al nombre de un adjunto al escribirlo
# (`file_manager.get_file_name`) si ya existe CUALQUIER File llamado igual, sin
# mirar a qué documento está adjunto. Con `overwrite=True` no debería ocurrir,
# pero quien BUSQUE el adjunto tiene que tolerarlo: es el mismo problema que
# hizo crecer sin fin los nombres de los .bpmn. Ver `sgc.bpmn_editor`.
_SUFIJO_HEX = re.compile(r"(?:[0-9a-f]{6})+$")


def nombre_pdf(ficha: str) -> str:
	"""El nombre del adjunto. Estable entre republicaciones, a propósito."""
	return f"ficha-{ficha}.pdf"


def es_el_pdf(file_name: str, ficha: str) -> bool:
	"""¿Este adjunto es el PDF de esta ficha, aunque Frappe le añadiera sufijo?"""
	if not file_name or not file_name.lower().endswith(".pdf"):
		return False
	esperado = nombre_pdf(ficha)[:-4].lower()
	tronco = _SUFIJO_HEX.sub("", file_name[:-4].lower())
	return tronco == esperado or file_name.lower() == nombre_pdf(ficha).lower()


def _render(ficha: str) -> bytes:
	"""Renderiza el Print Format. Aquí se paga el Chrome, una sola vez."""
	# `lang` fijado antes de renderizar: sin él, v16 falla al formatear fechas
	# cuando el lang de la request viene vacío (pasa en hooks y en jobs).
	frappe.local.lang = "es"
	return frappe.get_print(
		DOCTYPE,
		ficha,
		print_format=PRINT_FORMAT,
		as_pdf=True,
		pdf_generator="chrome",
	)


def _adjuntos_pdf(ficha: str):
	return [
		f
		for f in frappe.get_all(
			"File",
			filters={"attached_to_doctype": DOCTYPE, "attached_to_name": ficha},
			fields=["name", "file_name"],
		)
		if es_el_pdf(f.file_name, ficha)
	]


def pregenerar(ficha: str) -> dict:
	"""Escribe (o reescribe) el PDF de la ficha como adjunto. Idempotente."""
	contenido = _render(ficha)
	existentes = _adjuntos_pdf(ficha)

	if existentes:
		doc = frappe.get_doc("File", existentes[0].name)
		# Nunca más de uno: ver docstring del módulo.
		for sobrante in existentes[1:]:
			frappe.delete_doc("File", sobrante.name, ignore_permissions=True, force=True)
		# `ignore_existing_file_check=True` es imprescindible: sin él, `save_file`
		# deduplica por `content_hash` y, si otro File ya tiene ese contenido, da el
		# fichero por escrito y NO escribe, mientras el save() sí persiste hash y
		# tamaño nuevos. El registro diría tener la versión nueva y el disco la vieja.
		doc.save_file(content=contenido, overwrite=True, ignore_existing_file_check=True)
		doc.flags.ignore_permissions = True
		doc.save()
	else:
		from frappe.utils.file_manager import save_file

		doc = save_file(nombre_pdf(ficha), contenido, DOCTYPE, ficha, is_private=1)

	return {"file_name": doc.file_name, "file_url": doc.file_url}


def retirar(ficha: str) -> int:
	"""Borra el PDF pregenerado. Se usa al dejar de estar publicada.

	Necesario, no cosmético: mientras el fichero exista, se puede descargar —los
	adjuntos se sirven por permiso de doctype, sin mirar el estado del documento—.
	Despublicar sin borrarlo deja el contenido accesible a quien tenga la URL.
	"""
	borrados = 0
	for f in _adjuntos_pdf(ficha):
		frappe.delete_doc("File", f.name, ignore_permissions=True, force=True)
		borrados += 1
	return borrados


def sincronizar(doc, metodo=None):
	"""Hook de `on_update`: el PDF sigue al estado de la ficha.

	No se deja que un fallo de renderizado impida guardar la ficha: el PDF es un
	derivado, y perder el guardado del original por no poder dibujar el derivado
	sería el peor intercambio posible. Si falla, se registra y la ficha se guarda.
	"""
	publicada = doc.estado == ESTADO_PUBLICO
	try:
		if publicada:
			pregenerar(doc.name)
		else:
			retirar(doc.name)
	except Exception:
		frappe.log_error(
			title="Ficha PDF: no se pudo sincronizar el derivado",
			message=f"{doc.name} (estado={doc.estado})\n\n{frappe.get_traceback()}",
		)


@frappe.whitelist()
def pdf_publicado(ficha: str) -> dict | None:
	"""El PDF de una ficha, SOLO si la ficha está publicada.

	Existe para que el portal no tenga que razonar sobre adjuntos: pregunta por la
	ficha y recibe el fichero o nada. Comprueba el estado además del permiso porque
	el permiso de Frappe sobre los adjuntos NO mira el estado del documento padre.
	"""
	if not frappe.has_permission(DOCTYPE, ptype="read", doc=ficha):
		frappe.throw(_("Sin permiso sobre {0}").format(ficha), frappe.PermissionError)
	if frappe.db.get_value(DOCTYPE, ficha, "estado") != ESTADO_PUBLICO:
		return None
	adjuntos = _adjuntos_pdf(ficha)
	if not adjuntos:
		return None
	doc = frappe.get_doc("File", adjuntos[0].name)

	# Que exista el REGISTRO no garantiza que exista el FICHERO: son dos cosas
	# distintas y se pueden separar (un File huérfano de un intento fallido, un
	# borrado a mano en disco, una restauración de base sin sus adjuntos). Quien
	# llame a esto asumirá que puede servir lo que devuelve —y hará `open()`
	# directamente—, así que si el fichero no está, aquí se responde «no hay»
	# igual que si no hubiera registro. Un contrato que promete un fichero tiene
	# que comprobar el fichero.
	if not _existe_en_disco(doc):
		frappe.log_error(
			title="Ficha PDF: registro sin fichero",
			message=f"{ficha}: el File {doc.name} ({doc.file_name}) no tiene fichero en disco.",
		)
		return None

	return {"file_name": doc.file_name, "file_url": doc.file_url}


def _existe_en_disco(doc) -> bool:
	"""¿El File tiene de verdad su fichero detrás?"""
	try:
		ruta = doc.get_full_path()
	except Exception:
		return False
	return bool(ruta) and os.path.isfile(ruta)
