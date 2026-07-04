"""Detalle de un estándar — página a medida (autenticada).

Drill-down desde el Tablero: muestra los criterios del estándar con su
valoración (Cumple / Cumple parcial / No cumple) y el nivel resultante.
Parámetros: ?ae=<autoevaluacion>&est=<elemento_marco del estándar>
"""

import frappe

CUMPLE_META = {
    "Cumple": {"label": "Cumple", "color": "#1f7a46", "bg": "#e6f4ec"},
    "Cumple parcial": {"label": "Cumple parcial", "color": "#b7791f", "bg": "#fdf4e0"},
    "No cumple": {"label": "No cumple", "color": "#c0392b", "bg": "#fbecea"},
}
NIVEL_META = {
    "NL": {"label": "No logrado", "color": "#c0392b", "bg": "#fbecea"},
    "L": {"label": "Logrado", "color": "#b7791f", "bg": "#fdf4e0"},
    "LP": {"label": "Logrado plenamente", "color": "#1f7a46", "bg": "#e6f4ec"},
}
_FB = {"label": "Sin valorar", "color": "#5b6b7c", "bg": "#eef1f4"}


def get_context(context):
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/tablero"
        raise frappe.Redirect

    context.body_class = "sgc-estandar"
    context.title = "Detalle de estándar · SGC UPeU"

    ae = frappe.form_dict.get("ae")
    est = frappe.form_dict.get("est")

    if not ae:
        aes = frappe.get_all("Autoevaluacion", order_by="modified desc", limit_page_length=1, pluck="name")
        ae = aes[0] if aes else None

    context.estandar = None
    if not ae or not est or not frappe.db.exists("Elemento Marco", est):
        return context

    em = frappe.db.get_value("Elemento Marco", est, ["codigo", "denominacion", "texto_oficial"], as_dict=1) or {}
    context.estandar = {
        "codigo": em.get("codigo") or est,
        "nombre": em.get("denominacion") or "",
        "texto": em.get("texto_oficial") or "",
    }
    context.ae_codigo = frappe.db.get_value("Autoevaluacion", ae, "codigo") or ae

    nivel = frappe.db.get_value("Valoracion Estandar", {"autoevaluacion": ae, "elemento_marco": est}, "nivel_propuesto")
    context.nivel = nivel
    context.nivel_meta = NIVEL_META.get(nivel, _FB)

    criterios_raw = frappe.get_all(
        "Elemento Marco",
        {"parent_elemento_marco": est, "es_valorable": 1},
        ["name", "codigo", "denominacion"],
        limit_page_length=100,
    )
    criterios = []
    for c in criterios_raw:
        cumple = frappe.db.get_value("Valoracion Criterio", {"autoevaluacion": ae, "criterio": c.name}, "cumple")
        criterios.append({
            "codigo": c.get("codigo") or c.name,
            "nombre": c.get("denominacion") or "",
            "cumple": cumple,
            "meta": CUMPLE_META.get(cumple, _FB),
        })
    criterios.sort(key=lambda x: str(x["codigo"]))
    context.criterios = criterios
    context.resumen = {k: sum(1 for c in criterios if c["cumple"] == k) for k in CUMPLE_META}
    context.total = len(criterios)
    return context
