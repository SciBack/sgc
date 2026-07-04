"""Tablero de Acreditación — página a medida (autenticada) del SGC-UPeU.

Vista ejecutiva y bonita de una autoevaluación: avance, semáforo NL/L/LP por
estándar, y flujo CAPA. Control total de diseño (extiende base.html, sin el
chrome de Frappe). El escritorio (/app) queda para carga/edición de datos.
"""

import frappe

# Semántica de niveles CONEAU-SINEACE (Sección IX).
NIVEL_META = {
    "NL": {"label": "No logrado", "color": "#c0392b", "bg": "#fbecea"},
    "L": {"label": "Logrado", "color": "#b7791f", "bg": "#fdf4e0"},
    "LP": {"label": "Logrado plenamente", "color": "#1f7a46", "bg": "#e6f4ec"},
}
_FALLBACK = {"label": "Sin valorar", "color": "#5b6b7c", "bg": "#eef1f4"}


def _count(doctype, filters=None):
    try:
        return frappe.db.count(doctype, filters) if filters else frappe.db.count(doctype)
    except Exception:
        return 0


def get_context(context):
    context.no_cache = 1

    # --- requiere sesión (comité) ---
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/tablero"
        raise frappe.Redirect

    context.body_class = "sgc-tablero"
    context.title = "Tablero de Acreditación · SGC UPeU"

    aes = frappe.get_all(
        "Autoevaluacion",
        fields=["name", "codigo", "titulo", "marco_normativo", "programa_sede",
                "periodo_academico", "avance_pct", "vigencia_propuesta", "estado"],
        order_by="modified desc",
        limit_page_length=1,
    )
    if not aes:
        context.ae = None
        return context

    ae = aes[0]
    ps = frappe.db.get_value("Programa Sede", ae.programa_sede, ["programa", "sede"], as_dict=1) or {}
    ae["programa_nombre"] = frappe.db.get_value("Programa", ps.get("programa"), "nombre") or (ps.get("programa") or "")
    ae["sede_nombre"] = frappe.db.get_value("Unidad Organica", ps.get("sede"), "nombre") or (ps.get("sede") or "")
    ae["avance"] = int(round(float(ae.get("avance_pct") or 0)))
    context.ae = ae

    # --- estándares con su nivel ---
    ve = frappe.get_all(
        "Valoracion Estandar",
        {"autoevaluacion": ae.name},
        ["elemento_marco", "nivel", "nivel_propuesto"],
        limit_page_length=100,
    )
    estandares = []
    for x in ve:
        em = frappe.db.get_value("Elemento Marco", x.elemento_marco, ["codigo", "denominacion"], as_dict=1) or {}
        nivel = x.get("nivel_propuesto") or ""
        estandares.append({
            "name": x.elemento_marco,
            "codigo": em.get("codigo") or x.elemento_marco,
            "nombre": em.get("denominacion") or "",
            "nivel": nivel,
            "meta": NIVEL_META.get(nivel, _FALLBACK),
        })
    estandares.sort(key=lambda e: str(e["codigo"]))
    context.estandares = estandares

    context.resumen = {k: sum(1 for e in estandares if e["nivel"] == k) for k in ("NL", "L", "LP")}
    context.total_estandares = len(estandares)

    # --- métricas ---
    context.n_criterios = _count("Valoracion Criterio", {"autoevaluacion": ae.name})
    context.n_hallazgos = _count("Hallazgo")
    context.n_nc = _count("No Conformidad")
    context.n_planes = _count("Plan Mejora")
    context.n_evidencias = _count("Evidencia")
    context.n_indicadores = _count("Indicador")

    # ruta al registro en el escritorio (para editar)
    context.desk_url = "/app/autoevaluacion/" + ae.name
    return context
