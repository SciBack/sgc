# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Editor BPMN embebido (Fase 1).

Da soporte server-side a la página `bpmn-editor`: lista los .bpmn adjuntos a un
documento y guarda el XML editado de vuelta como adjunto (reemplazando la versión
anterior). El renderizado/edición es 100% cliente (bpmn-js Modeler self-hosted en
`sgc/public/bpmn/`), esto solo mueve el XML.

Decisión de origen: docs/decisiones/bpmn-herramientas.md, punto 2 (bpmn-js Modeler
en el sistema). El plan original lo ponía en la SPA (ya retirada); aquí vive como
Page del Desk nativo.

Alcance Fase 1: pensado para los BPMN institucionales (p.ej. los de DTI, 16/17), que
son manuales y NO llevan los `extensionElements` de rol/autoaprobación de los 15
workflows generados. Editar y guardar un BPMN generado desde aquí NO está habilitado
hasta medir si bpmn-js conserva esos metadatos (riesgo abierto del doc citado).
"""
import re

import frappe
from frappe import _

# Frappe puede añadir `content_hash[-6:]` al nombre de un adjunto al escribirlo
# (`file_manager.get_file_name`). Para volver a encontrar ESE adjunto en el
# siguiente guardado hay que comparar por el nombre de partida, no por el que
# quedó: si no, no se reconoce, se crea otro, y el nombre crece guardado a
# guardado. Se recortan sufijos hexadecimales en bloques de 6.
_SUFIJO_HEX = re.compile(r"(?:[0-9a-f]{6})+$")


def _check(doctype, docname, ptype="read"):
    if not frappe.has_permission(doctype, ptype=ptype, doc=docname):
        frappe.throw(_("No tiene permiso de {0} sobre {1} {2}").format(ptype, doctype, docname),
                     frappe.PermissionError)


@frappe.whitelist()
def listar_bpmn(doctype, docname):
	"""Devuelve los adjuntos .bpmn del documento: [{file_name, file_url, name}]."""
	_check(doctype, docname, "read")
	filas = frappe.get_all(
		"File",
		filters={"attached_to_doctype": doctype, "attached_to_name": docname},
		fields=["name", "file_name", "file_url"],
		order_by="file_name asc",
	)
	return [f for f in filas if (f.get("file_name") or "").lower().endswith(".bpmn")]


def _base_del_nombre(nombre):
	"""Nombre sin extensión y sin los sufijos que Frappe haya podido añadirle."""
	nombre = (nombre or "").strip()
	tronco = nombre[:-5] if nombre.lower().endswith(".bpmn") else nombre
	return _SUFIJO_HEX.sub("", tronco).lower()


def _mismo_diagrama(a, b):
	"""¿Estos dos nombres de adjunto son el mismo diagrama?

	`18-proceso.bpmn`, `18-procesoa1b2c3.bpmn` y `18-procesoa1b2c3d4e5f6.bpmn` lo son:
	los dos últimos son el primero después de que Frappe le añadiera su sufijo.
	"""
	if not a or not b:
		return False
	if a == b:
		return True
	base_a, base_b = _base_del_nombre(a), _base_del_nombre(b)
	return bool(base_a) and base_a == base_b


@frappe.whitelist()
def guardar_bpmn(doctype, docname, file_name, xml):
	"""Reemplaza (o crea) el adjunto .bpmn `file_name` del documento con `xml`."""
	_check(doctype, docname, "write")
	if not (file_name or "").lower().endswith(".bpmn"):
		frappe.throw(_("El nombre de archivo debe terminar en .bpmn"))
	if "<bpmn:definitions" not in xml and "<definitions" not in xml:
		frappe.throw(_("El contenido no parece un BPMN válido"))

	contenido = xml.encode("utf-8")
	existentes = [
		f.name
		for f in frappe.get_all(
			"File",
			filters={"attached_to_doctype": doctype, "attached_to_name": docname},
			fields=["name", "file_name"],
		)
		if _mismo_diagrama(f.file_name, file_name)
	]

	if existentes:
		# Se reescribe el MISMO File en su sitio, en vez de borrarlo y crear otro.
		#
		# Borrar y recrear hacía que el adjunto se RENOMBRARA en cada guardado:
		# `file_manager.save_file` pasa siempre por `get_file_name`, que añade
		# `content_hash[-6:]` al nombre si existe CUALQUIER File llamado igual —sin
		# mirar a qué documento está adjunto—. Como el mismo diagrama suele estar
		# adjunto también a la ficha del proceso, la colisión es permanente y el
		# nombre crecía sin fin: `…-dti.bpmn` → `…-dtie65eede65eed.bpmn` →
		# `…-dtie65eede65eed6a79bd.bpmn`. Verificado en producción.
		#
		# `File.save_file(overwrite=True)` salta esa generación de nombre y sobrescribe
		# el fichero en disco, que es justo lo que queremos: el adjunto conserva su
		# nombre y su URL, y quien lo tuviera abierto no pierde la referencia.
		f = frappe.get_doc("File", existentes[0])
		for sobrante in existentes[1:]:
			frappe.delete_doc("File", sobrante, ignore_permissions=True, force=True)
		# `ignore_existing_file_check=True` es imprescindible, no una precaución.
		# Sin él, `File.save_file` deduplica por `content_hash`: si YA existe otro File
		# con ese mismo contenido —el caso normal al sincronizar el mismo diagrama entre
		# el procedimiento y la ficha del proceso— da el fichero por escrito y **no
		# escribe nada**, mientras el `save()` de abajo sí persiste el hash y el tamaño
		# nuevos. El registro queda diciendo que tiene la versión nueva y el disco
		# conservando la vieja. Comprobado en producción: `content_hash` 76b2648f con un
		# fichero cuyo hash real era 49312bc0.
		f.save_file(content=contenido, overwrite=True, ignore_existing_file_check=True)
		f.flags.ignore_permissions = True
		f.save()
		frappe.db.commit()
		return {"ok": True, "file_url": f.file_url, "file_name": f.file_name}

	from frappe.utils.file_manager import save_file

	f = save_file(file_name, contenido, doctype, docname, is_private=1)
	frappe.db.commit()
	return {"ok": True, "file_url": f.file_url, "file_name": f.file_name}
