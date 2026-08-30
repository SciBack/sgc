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
import frappe
from frappe import _


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


@frappe.whitelist()
def guardar_bpmn(doctype, docname, file_name, xml):
	"""Reemplaza (o crea) el adjunto .bpmn `file_name` del documento con `xml`."""
	_check(doctype, docname, "write")
	if not (file_name or "").lower().endswith(".bpmn"):
		frappe.throw(_("El nombre de archivo debe terminar en .bpmn"))
	if "<bpmn:definitions" not in xml and "<definitions" not in xml:
		frappe.throw(_("El contenido no parece un BPMN válido"))

	# borrar la versión anterior con ese nombre
	for f in frappe.get_all(
		"File",
		filters={"attached_to_doctype": doctype, "attached_to_name": docname, "file_name": file_name},
	):
		frappe.delete_doc("File", f.name, ignore_permissions=True, force=True)

	from frappe.utils.file_manager import save_file

	f = save_file(file_name, xml.encode("utf-8"), doctype, docname, is_private=1)
	frappe.db.commit()
	return {"ok": True, "file_url": f.file_url, "file_name": f.file_name}
