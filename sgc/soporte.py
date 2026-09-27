# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Canal de soporte (#56): reportar un problema desde el propio sistema.

No es un sistema de tickets: el ticket vive en el helpdesk de la institución
(Zammad, el helpdesk del catálogo, o un buzón de correo). Esto es el punto de
entrada y lo que viaja con él.

Qué viaja, y nada más:

- lo que escribe quien reporta (asunto, prioridad y descripción);
- un contexto técnico de lista blanca (`CAMPOS_CONTEXTO`): sistema, institución,
  sitio, versiones, usuario y roles de quien reporta, y la pantalla en la que
  estaba **sin el identificador del registro** (`pantalla`).

Nunca el contenido del documento abierto ni datos de otras personas. Quien
reporta ve el texto completo antes de enviarlo (`previsualizar`). Sin canal
configurado, el menú no aparece y los métodos se niegan. Si el helpdesk no
responde, no hay error genérico: vuelve un mensaje claro, la alternativa y el
texto listo para copiar.
"""

import re
from urllib.parse import unquote

import frappe
import requests
from frappe import _
from frappe.permissions import AUTOMATIC_ROLES

import sgc

CONFIG = "Configuracion Soporte"
PRIORIDADES = ("Baja", "Media", "Alta")
MAX_ASUNTO = 140
MAX_DESCRIPCION = 5000

# El contexto técnico, en este orden. Añadir un campo aquí es decidir que viaja.
CAMPOS_CONTEXTO = (
    "Sistema", "Institución", "Sitio", "Versión SGC", "Versión Frappe",
    "Usuario", "Roles", "Pantalla",
)

# Segundo tramo de una ruta del Desk que no es un registro.
_VISTAS = {"view", "tree", "report", "kanban", "calendar", "gantt", "dashboard", "image", "inbox"}


class CanalCaido(Exception):
    """El helpdesk no respondió o rechazó el ticket."""


def _config():
    return frappe.get_single(CONFIG)


def estado():
    """Lo que el navegador necesita saber del canal. Sin secretos."""
    c = _config()
    return {"activo": bool(c.activo), "alternativa": c.correo_soporte or None}


def boot(bootinfo):
    """`extend_bootinfo`: el menú «Reportar un problema» lo condiciona a esto."""
    if frappe.session.user != "Guest":
        bootinfo.sgc_soporte = estado()


def _limpio(texto, largo):
    return re.sub(r"[^\w\- ]", "", texto or "", flags=re.UNICODE)[:largo]


def pantalla(ruta):
    """La pantalla en la que estaba quien reporta, SIN el identificador del registro.

    «/desk/no-conformidad/NC-2026-00015» -> «no-conformidad (un registro)». El
    nombre de un registro puede ser el correo de otra persona (`/desk/user/...`)
    o delatar de qué caso se trata: no viaja. El nombre de la pantalla o del
    informe sí, que es del producto.
    """
    partes = [p for p in (ruta or "").split("?")[0].strip("/").split("/") if p]
    if partes[:1] in (["desk"], ["app"]):
        partes = partes[1:]
    if not partes:
        return _("Inicio")
    base = _limpio(partes[0], 60)
    if base == "query-report" and len(partes) > 1:
        return _("Informe: {0}").format(_limpio(unquote(partes[1]), 80))
    if len(partes) == 1:
        return base
    if partes[1] in _VISTAS:
        return _("{0} (vista)").format(base)
    if partes[1].startswith("new"):
        return _("{0} (nuevo registro)").format(base)
    return _("{0} (un registro)").format(base)


def contexto(ruta=None):
    """El contexto técnico de lista blanca. Nada que no esté en CAMPOS_CONTEXTO."""
    usuario = frappe.session.user
    roles = sorted(r for r in frappe.get_roles(usuario) if r not in AUTOMATIC_ROLES)
    valores = {
        "Sistema": frappe.conf.get("sgc_app_name") or "SGC",
        "Institución": frappe.conf.get("sgc_institucion") or "",
        "Sitio": frappe.utils.get_url(),
        "Versión SGC": sgc.__version__,
        "Versión Frappe": frappe.__version__,
        "Usuario": usuario,
        "Roles": ", ".join(roles),
        "Pantalla": pantalla(ruta),
    }
    return {k: valores[k] for k in CAMPOS_CONTEXTO}


def componer(asunto, descripcion, prioridad="Media", ruta=None):
    """El ticket tal cual se enviará: lo que se previsualiza es lo que sale."""
    asunto = " ".join((asunto or "").split())
    descripcion = (descripcion or "").strip()
    if not asunto:
        frappe.throw(_("Escriba un asunto: en una línea, qué no funciona."))
    if not descripcion:
        frappe.throw(_("Describa el problema: qué hacía, qué esperaba y qué pasó."))
    if len(asunto) > MAX_ASUNTO:
        frappe.throw(_("El asunto admite hasta {0} caracteres.").format(MAX_ASUNTO))
    if len(descripcion) > MAX_DESCRIPCION:
        frappe.throw(_("La descripción admite hasta {0} caracteres.").format(MAX_DESCRIPCION))
    if prioridad not in PRIORIDADES:
        frappe.throw(_("La prioridad es Baja, Media o Alta."))

    ctx = contexto(ruta)
    cuerpo = "{0}\n\n— {1} —\n{2}".format(
        descripcion, _("Contexto técnico"), "\n".join(f"{k}: {v}" for k, v in ctx.items())
    )
    return {"asunto": asunto, "prioridad": prioridad, "cuerpo": cuerpo, "contexto": ctx}


def _exigir_canal():
    c = _config()
    if not c.activo:
        frappe.throw(_("No hay un canal de soporte configurado en este sistema."), title=_("Sin canal de soporte"))
    return c


@frappe.whitelist()
def previsualizar(asunto, descripcion, prioridad="Media", ruta=None):
    _exigir_canal()
    return componer(asunto, descripcion, prioridad, ruta)


@frappe.whitelist(methods=["POST"])
def reportar(asunto, descripcion, prioridad="Media", ruta=None):
    """Crea el ticket. Si el helpdesk no responde, devuelve la alternativa, no un error."""
    c = _exigir_canal()
    ticket = componer(asunto, descripcion, prioridad, ruta)
    try:
        if c.proveedor == "Zammad":
            referencia = _zammad(c, ticket)
        else:
            referencia = _correo(c, ticket)
    except CanalCaido as e:
        # El motivo técnico (HTTP, timeout) va al registro de errores; el token no.
        frappe.log_error(title=_("Soporte: el helpdesk no recibió el ticket"), message=str(e))
        return {
            "ok": False,
            "mensaje": _("El helpdesk no respondió y su reporte no se envió."),
            "alternativa": c.correo_soporte or None,
            "texto": "{0}\n\n{1}".format(ticket["asunto"], ticket["cuerpo"]),
        }
    return {"ok": True, "referencia": referencia, "proveedor": c.proveedor}


def _zammad(c, ticket):
    correo = frappe.db.get_value("User", frappe.session.user, "email") or frappe.session.user
    prioridad = {
        "Baja": c.prioridad_baja or "1 low",
        "Media": c.prioridad_media or "2 normal",
        "Alta": c.prioridad_alta or "3 high",
    }[ticket["prioridad"]]
    carga = {
        "title": ticket["asunto"],
        "group": c.zammad_grupo,
        # A nombre de quien reporta; lo crea si no existe (exige permiso de agente).
        "customer_id": f"guess:{correo}",
        "priority": prioridad,
        "article": {
            "subject": ticket["asunto"],
            "body": ticket["cuerpo"],
            "content_type": "text/plain",
            "type": "web",
            # Sin esto Zammad lo registra como escrito por un agente.
            "sender": "Customer",
            "internal": False,
        },
    }
    try:
        r = requests.post(
            c.zammad_url.rstrip("/") + "/api/v1/tickets",
            json=carga,
            headers={"Authorization": "Token token={0}".format(c.get_password("zammad_token"))},
            timeout=c.tiempo_espera or 10,
        )
    except requests.RequestException as e:
        raise CanalCaido(type(e).__name__) from None
    if r.status_code not in (200, 201):
        raise CanalCaido(f"HTTP {r.status_code}")
    try:
        datos = r.json()
    except ValueError:
        raise CanalCaido(_("respuesta sin JSON")) from None
    return str(datos.get("number") or datos.get("id") or "")


def _correo(c, ticket):
    from sgc.correo import enviar

    cuerpo = "<pre style=\"white-space: pre-wrap; font-family: inherit\">{0}</pre>".format(
        frappe.utils.escape_html(ticket["cuerpo"])
    )
    resultado = enviar(
        [c.correo_soporte],
        "[{0}] {1}".format(ticket["prioridad"], ticket["asunto"]),
        cuerpo,
        origen="Soporte",
    )
    if not resultado["enviados"]:
        # Retenido por el modo de ensayo o la lista blanca: no llegó a nadie.
        raise CanalCaido(_("retenido por la configuración del correo"))
    return c.correo_soporte
