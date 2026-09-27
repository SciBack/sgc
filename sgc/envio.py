# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Enviar un documento o una ficha por correo, a usuarios o a cualquier dirección (#92).

Lo que se puede enviar y cómo:

- Solo lo **publicado**: un borrador no sale de la institución por correo.
- Un documento de **solo consulta** (#36) sale sin su archivo, solo con el enlace:
  el correo es otra puerta de descarga y ya estaba cerrada para las reglas.
- La ficha de caracterización va en PDF. Si algún destinatario es externo, va en
  el formato **público**, sin los nombres de quienes firman (Ley 29733: publicar
  de más también incumple; ver f19_ficha_pdf).
- Lo envían los roles que gobiernan la documentación, no cualquiera que la lea.

Todo pasa por `sgc.correo.enviar`: modo de ensayo, lista blanca y registro.
"""

import frappe
from frappe import _
from frappe.utils import get_url_to_form

from sgc.correo import enviar, es_correo
from sgc.documentos import EXTERNA

ROLES_QUE_ENVIAN = {"DPGC", "Analista de Calidad (DPGC)", "Dueño de Proceso", "System Manager"}
MAX_DESTINATARIOS = 50

FICHA = "Ficha Caracterizacion Proceso"
DOCUMENTO = "Documento Controlado"
ENVIABLES = {DOCUMENTO: "Publicado", FICHA: "Publicado"}

FORMATO_FICHA = "Ficha de Caracterizacion"
FORMATO_FICHA_PUBLICO = "Ficha de Caracterizacion (publico)"


def _lista(valor):
    if not valor:
        return []
    if isinstance(valor, str):
        valor = frappe.parse_json(valor) if valor.strip().startswith("[") else valor.replace(";", ",").replace("\n", ",").split(",")
    return [v.strip() for v in valor if v and v.strip()]


def destinatarios(usuarios, externos):
    """(correos, hay_externos). Valida las direcciones y el tope."""
    correos = []
    for u in _lista(usuarios):
        correo, activo = frappe.db.get_value("User", u, ["email", "enabled"]) or (None, 0)
        if not correo or not activo:
            frappe.throw(_("El usuario {0} no existe, está desactivado o no tiene correo.").format(u))
        correos.append(correo)

    ext = _lista(externos)
    malos = [e for e in ext if not es_correo(e)]
    if malos:
        frappe.throw(_("Direcciones no válidas: {0}").format(", ".join(malos)),
                     title=_("Correo no válido"))
    internos = {c.lower() for c in correos}
    externos_reales = [e for e in ext if e.lower() not in internos
                       and not frappe.db.exists("User", {"email": e, "enabled": 1})]
    correos += ext

    if not correos:
        frappe.throw(_("Indique al menos un destinatario."))
    if len(correos) > MAX_DESTINATARIOS:
        frappe.throw(_("Como máximo {0} destinatarios por envío.").format(MAX_DESTINATARIOS))
    return correos, bool(externos_reales)


def _validar_quien_y_que(doctype, name):
    if doctype not in ENVIABLES:
        frappe.throw(_("Este tipo de documento no se envía por correo desde aquí."))
    doc = frappe.get_doc(doctype, name)
    doc.check_permission("read")
    if not ROLES_QUE_ENVIAN & set(frappe.get_roles()):
        frappe.throw(_("Enviar documentos por correo es de quien gobierna la documentación "
                       "(DPGC, su analista o el dueño del proceso)."), frappe.PermissionError)
    if doc.get("estado") != ENVIABLES[doctype]:
        frappe.throw(_("Solo se envía lo publicado. Estado actual: «{0}».").format(doc.get("estado")),
                     title=_("Sin publicar"))
    return doc


def _adjunto_documento(doc):
    """El archivo del documento, salvo que sea de solo consulta o no lo tenga."""
    if doc.get("solo_consulta") or not doc.get("archivo"):
        return []
    fichero = frappe.db.get_value("File", {"file_url": doc.archivo, "attached_to_doctype": DOCUMENTO,
                                           "attached_to_name": doc.name}, "name")
    return [fichero] if fichero else []


@frappe.whitelist()
def enviar_por_correo(doctype, name, usuarios=None, externos=None, mensaje=None):
    doc = _validar_quien_y_que(doctype, name)
    correos, hay_externos = destinatarios(usuarios, externos)

    titulo = doc.get("titulo") or doc.name
    enlace = get_url_to_form(doctype, doc.name)
    cuerpo = []
    if (mensaje or "").strip():
        cuerpo.append("<p>{0}</p>".format(frappe.utils.escape_html(mensaje).replace("\n", "<br>")))

    adjuntos, formato = [], None
    if doctype == DOCUMENTO:
        adjuntos = _adjunto_documento(doc)
        if doc.get("tipo_documento") == EXTERNA and doc.get("url_externa"):
            cuerpo.append('<p>Documento externo: <a href="{0}">{0}</a></p>'.format(doc.url_externa))
        if doc.get("solo_consulta"):
            cuerpo.append("<p>Este documento es de solo consulta: se consulta en el sistema, "
                          "no se distribuye el archivo.</p>")
        asunto = _("Documento controlado {0}: {1}").format(doc.name, titulo)
    else:
        formato = FORMATO_FICHA_PUBLICO if hay_externos else FORMATO_FICHA
        if not frappe.db.exists("Print Format", formato):
            formato = None
        asunto = _("Ficha de caracterización {0}").format(titulo)
    cuerpo.append('<p><a href="{0}">Abrir en el SGC</a> (requiere acceso)</p>'.format(enlace))

    resultado = enviar(correos, asunto, "".join(cuerpo), doctype, doc.name,
                       origen="Envío manual", adjuntos=adjuntos, formato_impresion=formato)
    resultado["formato"] = formato
    return resultado
