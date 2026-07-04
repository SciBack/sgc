"""Mejora Continua (CAPA) — página a medida (autenticada).

Recorre el ciclo: Hallazgo → No Conformidad → Plan de Mejora → Acciones.
Parámetro opcional: ?ae=<autoevaluacion> (por defecto, la más reciente).
"""

import frappe


def _estado_color(estado):
    e = (estado or "").lower()
    if e in ("cerrado", "resuelto", "completado", "implementado", "eficaz"):
        return {"color": "#1f7a46", "bg": "#e6f4ec"}
    if e in ("abierto", "en proceso", "pendiente", "planificado", "en ejecucion"):
        return {"color": "#b7791f", "bg": "#fdf4e0"}
    return {"color": "#5b6b7c", "bg": "#eef1f4"}


def _sev_color(sev):
    s = (sev or "").lower()
    if s in ("alta", "critica", "mayor"):
        return {"color": "#c0392b", "bg": "#fbecea"}
    if s in ("media", "moderada"):
        return {"color": "#b7791f", "bg": "#fdf4e0"}
    return {"color": "#1f7a46", "bg": "#e6f4ec"}


def _ae_filter(ae, field="autoevaluacion"):
    return {field: ae} if ae else None


def get_context(context):
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/tablero"
        raise frappe.Redirect

    context.body_class = "sgc-mejora"
    context.title = "Mejora Continua · SGC UPeU"

    ae = frappe.form_dict.get("ae")
    if not ae:
        aes = frappe.get_all("Autoevaluacion", order_by="modified desc", limit_page_length=1, pluck="name")
        ae = aes[0] if aes else None
    context.ae_name = ae
    context.ae_codigo = frappe.db.get_value("Autoevaluacion", ae, "codigo") if ae else None

    hs = frappe.get_all("Hallazgo", _ae_filter(ae),
                        ["codigo", "tipo", "severidad", "estado", "criterio", "descripcion"],
                        order_by="codigo", limit_page_length=200)
    for h in hs:
        h["estado_meta"] = _estado_color(h.get("estado"))
        h["sev_meta"] = _sev_color(h.get("severidad"))
    context.hallazgos = hs

    ncs = frappe.get_all("No Conformidad",
                         ["name", "titulo", "criterio", "estado", "severidad"],
                         order_by="creation", limit_page_length=200)
    for n in ncs:
        n["estado_meta"] = _estado_color(n.get("estado"))
    context.no_conformidades = ncs

    planes = frappe.get_all("Plan Mejora", _ae_filter(ae),
                            ["name", "codigo", "titulo", "estado", "responsable"],
                            order_by="codigo", limit_page_length=200)
    for p in planes:
        p["estado_meta"] = _estado_color(p.get("estado"))
        acc = frappe.get_all("Accion Mejora", {"plan_mejora": p.name},
                             ["codigo", "descripcion", "estado", "avance_pct", "tipo"], limit_page_length=50)
        for a in acc:
            a["estado_meta"] = _estado_color(a.get("estado"))
            a["avance"] = int(round(float(a.get("avance_pct") or 0)))
        p["acciones"] = acc
    context.planes = planes

    context.n_hallazgos = len(hs)
    context.n_nc = len(ncs)
    context.n_planes = len(planes)
    context.n_acciones = sum(len(p["acciones"]) for p in planes)
    return context
