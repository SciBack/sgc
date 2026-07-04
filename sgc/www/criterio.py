"""Detalle de un criterio — página a medida (autenticada).

Drill-down: Tablero → Estándar → Criterio. Muestra la valoración del criterio
(Cumple / parcial / No cumple), la observación/debilidad, hallazgos vinculados
y evidencias. Parámetros: ?ae=<autoevaluacion>&crit=<elemento_marco criterio>
"""

import frappe

CUMPLE_META = {
    "Cumple": {"label": "Cumple", "color": "#1f7a46", "bg": "#e6f4ec"},
    "Cumple parcial": {"label": "Cumple parcial", "color": "#b7791f", "bg": "#fdf4e0"},
    "No cumple": {"label": "No cumple", "color": "#c0392b", "bg": "#fbecea"},
}
_FB = {"label": "Sin valorar", "color": "#5b6b7c", "bg": "#eef1f4"}


def _estado_color(estado):
    e = (estado or "").lower()
    if e in ("cerrado", "resuelto", "completado"):
        return {"color": "#1f7a46", "bg": "#e6f4ec"}
    if e in ("abierto", "en proceso", "pendiente"):
        return {"color": "#b7791f", "bg": "#fdf4e0"}
    return {"color": "#5b6b7c", "bg": "#eef1f4"}


def get_context(context):
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/tablero"
        raise frappe.Redirect

    context.body_class = "sgc-criterio"
    context.title = "Detalle de criterio · SGC UPeU"

    ae = frappe.form_dict.get("ae")
    crit = frappe.form_dict.get("crit")
    if not ae:
        aes = frappe.get_all("Autoevaluacion", order_by="modified desc", limit_page_length=1, pluck="name")
        ae = aes[0] if aes else None

    context.criterio = None
    if not ae or not crit or not frappe.db.exists("Elemento Marco", crit):
        return context

    em = frappe.db.get_value("Elemento Marco", crit, ["codigo", "denominacion", "texto_oficial", "parent_elemento_marco"], as_dict=1) or {}
    context.criterio = {"codigo": em.get("codigo") or crit, "nombre": em.get("denominacion") or "", "texto": em.get("texto_oficial") or ""}
    context.ae_name = ae
    context.ae_codigo = frappe.db.get_value("Autoevaluacion", ae, "codigo") or ae

    parent = em.get("parent_elemento_marco")
    context.estandar_name = parent
    context.estandar_codigo = frappe.db.get_value("Elemento Marco", parent, "codigo") if parent else None

    vc = frappe.db.get_value(
        "Valoracion Criterio", {"autoevaluacion": ae, "criterio": crit},
        ["cumple", "observacion", "debilidad", "comentario", "estado"], as_dict=1) or {}
    cumple = vc.get("cumple")
    context.valoracion = {
        "cumple": cumple,
        "meta": CUMPLE_META.get(cumple, _FB),
        "observacion": vc.get("observacion") or "",
        "debilidad": vc.get("debilidad") or "",
        "comentario": vc.get("comentario") or "",
        "estado": vc.get("estado") or "",
    }

    hs = frappe.get_all("Hallazgo", {"autoevaluacion": ae, "criterio": crit},
                        ["codigo", "tipo", "severidad", "estado", "descripcion"], limit_page_length=20)
    for h in hs:
        h["estado_meta"] = _estado_color(h.get("estado"))
    context.hallazgos = hs

    vc_name = frappe.db.get_value("Valoracion Criterio", {"autoevaluacion": ae, "criterio": crit}, "name")
    evid = frappe.get_all("Evidencia", filters={"origen_doctype": "Elemento Marco", "origen_id": crit},
                          fields=["codigo", "titulo", "tipo", "descripcion"], limit_page_length=20)
    if vc_name:
        evid += frappe.get_all("Evidencia", filters={"origen_doctype": "Valoracion Criterio", "origen_id": vc_name},
                               fields=["codigo", "titulo", "tipo", "descripcion"], limit_page_length=20)
    context.evidencias = evid
    return context
