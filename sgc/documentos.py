"""Copias controladas: consulta en pantalla sin descarga, y registro de accesos (#36).

En un sistema documental hay documentos que se consultan pero no se llevan: el
control de copias es lo que impide que circule una versión obsoleta en el
escritorio de alguien. Un documento marcado `solo_consulta` lo **descarga solo
quien puede editarlo**; el resto lo ve en el visor de la ficha.

**Es un control disuasorio, no una garantía.** Quien ve el contenido puede
capturarlo. Lo que sí garantiza es que el fichero no se entrega por ninguna de
las puertas del sistema, y que cada consulta y cada descarga queda registrada.

**Las cuatro puertas al contenido de un fichero**, y dónde se cierra cada una:

1. `/private/files/…` → `download_private_file` → `find_file_by_url` →
   `File.is_downloadable()` (frappe/utils/response.py:294-306).
2. `/api/method/download_file` → `find_file_by_url` → lo mismo
   (frappe/handler.py:237-252). Las dos se cierran en `FicheroSGC`.
3. `frappe.core.api.file.zip_files` → `File.zip_files`, que llama a la
   `has_permission` del módulo `file.py` y NO a `is_downloadable` ni a los hooks
   de la app (file.py:971). Se cierra en `zip_files` de aquí, registrado en
   `override_whitelisted_methods`.
4. La regla de correo de publicación adjunta el `archivo` (f15). Se cierra en
   `sgc.correo.NotificacionSGC.get_attachment`.

Un hook `has_permission` sobre `File` NO serviría: ninguna de las tres primeras
puertas pasa por él.

**El registro.** Frappe ya deja un `Access Log` en cada descarga por la puerta 1,
contra el `File`. El visor y la descarga desde la ficha dejan el suyo contra el
documento, con `method` = Consulta o Descarga. `make_access_log` usa
`deferred_insert`, que funciona también en una petición GET (frappe no confirma
la transacción en GET). El informe «Accesos a Documentos» los une.
"""

import os
import re

import frappe
from frappe import _
from frappe.core.api.file import zip_files as _zip_files_frappe
from frappe.core.doctype.access_log.access_log import make_access_log
from frappe.core.doctype.file.file import File

DOCTYPE = "Documento Controlado"
EXTERNA = "Documentación externa"

CONSULTA = "Consulta"
DESCARGA = "Descarga"

# Lo que un navegador dibuja sin ejecutar nada. SVG no: servido en línea desde
# el propio dominio puede llevar script (Frappe lo fuerza a descarga por eso,
# frappe/utils/response.py:309).
EMBEBIBLES = {"pdf", "png", "jpg", "jpeg", "gif", "webp"}

_URL_VALIDA = re.compile(r"^https?://\S+$", re.IGNORECASE)


# --- reglas (puras) ------------------------------------------------------------


def extension(url):
	return os.path.splitext((url or "").split("?")[0])[1].lstrip(".").lower()


def se_puede_ver_en_pantalla(url):
	return extension(url) in EMBEBIBLES


def url_externa_valida(url):
	return bool(_URL_VALIDA.match((url or "").strip()))


# --- quién descarga -------------------------------------------------------------


def puede_descargar(doc, user=None):
	"""Quien puede leer el documento lo descarga, salvo que sea de solo consulta.

	De solo consulta: solo quien puede **editarlo** —quien lo elabora, lo revisa o
	lo administra— y Administrator.
	"""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	if not frappe.has_permission(DOCTYPE, "read", doc=doc, user=user):
		return False
	if not doc.get("solo_consulta"):
		return True
	return bool(frappe.has_permission(DOCTYPE, "write", doc=doc, user=user))


def _documento_de_solo_consulta(fichero):
	if fichero.attached_to_doctype != DOCTYPE or not fichero.attached_to_name:
		return None
	if not frappe.db.get_value(DOCTYPE, fichero.attached_to_name, "solo_consulta"):
		return None
	return frappe.get_doc(DOCTYPE, fichero.attached_to_name)


class FicheroSGC(File):
	"""`File` que no entrega el adjunto de un documento de solo consulta.

	Cierra las puertas 1 y 2 (ver el docstring del módulo). Se registra en
	`override_doctype_class`.
	"""

	def is_downloadable(self):
		if not super().is_downloadable():
			return False
		doc = _documento_de_solo_consulta(self)
		return doc is None or puede_descargar(doc)


@frappe.whitelist()
def zip_files(files: str):
	"""`frappe.core.api.file.zip_files`, sin los ficheros que no se pueden descargar.

	El original comprueba la lectura del `File`, no si se puede descargar
	(puerta 3). Se quitan antes de delegar en él.
	"""
	permitidos = []
	for nombre in frappe.parse_json(files) or []:
		if isinstance(nombre, str) and frappe.db.exists("File", nombre):
			if frappe.get_doc("File", nombre).is_downloadable():
				permitidos.append(nombre)
	return _zip_files_frappe(frappe.as_json(permitidos))


# --- el visor y la descarga desde la ficha -------------------------------------


def _fichero(doc):
	"""El `File` del campo `archivo`, el que está colgado de este documento."""
	nombre = frappe.db.get_value(
		"File",
		{"file_url": doc.archivo, "attached_to_doctype": DOCTYPE, "attached_to_name": doc.name},
		"name",
	) or frappe.db.get_value("File", {"file_url": doc.archivo}, "name")
	if not nombre:
		frappe.throw(_("No se encuentra el archivo de {0}.").format(doc.name), frappe.DoesNotExistError)
	return frappe.get_doc("File", nombre)


def _bytes(fichero):
	"""El contenido tal cual está en disco.

	No `File.get_content()`: intenta decodificarlo como texto y, entre sus
	codificaciones, `windows-1252` acepta casi cualquier byte
	(file.py:45 y 713-723). Un PDF que pasara por ahí volvería como `str` y
	llegaría corrupto al navegador.
	"""
	fichero.validate_file_path()
	fichero.validate_file_url()
	with open(fichero.get_full_path(), "rb") as f:
		return f.read()


def _servir(doc, como, accion):
	fichero = _fichero(doc)
	make_access_log(doctype=DOCTYPE, document=doc.name, method=accion, file_type=extension(doc.archivo))
	frappe.local.response.filename = fichero.file_name
	frappe.local.response.filecontent = _bytes(fichero)
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = como


@frappe.whitelist(methods=["GET"])
def ver(nombre: str):
	"""El documento, para dibujarlo en el visor. Basta con poder leerlo."""
	doc = frappe.get_doc(DOCTYPE, nombre)
	doc.check_permission("read")
	if not doc.archivo:
		frappe.throw(_("{0} no tiene archivo.").format(nombre))
	if not se_puede_ver_en_pantalla(doc.archivo):
		frappe.throw(_("Este formato no se puede ver en pantalla."))
	_servir(doc, "inline", CONSULTA)


@frappe.whitelist(methods=["GET"])
def descargar(nombre: str):
	"""El documento como descarga, si quien lo pide puede llevárselo."""
	doc = frappe.get_doc(DOCTYPE, nombre)
	doc.check_permission("read")
	if not doc.archivo:
		frappe.throw(_("{0} no tiene archivo.").format(nombre))
	if not puede_descargar(doc):
		frappe.throw(
			_("{0} es de solo consulta: se lee en pantalla y no se descarga.").format(nombre),
			frappe.PermissionError,
		)
	_servir(doc, "attachment", DESCARGA)
