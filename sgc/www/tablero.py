"""Tablero de Acreditación — página a medida (autenticada) del SGC-UPeU.

Vista ejecutiva y bonita de una autoevaluación: avance, semáforo NL/L/LP por
estándar, y flujo CAPA. Control total de diseño (extiende base.html, sin el
chrome de Frappe). El escritorio (/app) queda para carga/edición de datos.
"""

import frappe

from sgc.informe import _nivel_de_estandar

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
    # Fase 2 (2026-07-19, hallazgo): antes leía solo `nivel_propuesto`, ignorando
    # el `nivel` oficial confirmado por el comité -> contradecía a informe.py y
    # tablero_ejecutivo.py, que sí lo priorizan. Ahora usa el mismo helper que
    # informe.py para que las 3 vistas sean consistentes.
    ve = frappe.get_all(
        "Valoracion Estandar",
        {"autoevaluacion": ae.name},
        ["elemento_marco"],
        limit_page_length=100,
    )
    estandares = []
    for x in ve:
        em = frappe.db.get_value("Elemento Marco", x.elemento_marco, ["codigo", "denominacion"], as_dict=1) or {}
        sigla, confirmado, _just = _nivel_de_estandar(ae.name, x.elemento_marco)
        nivel = sigla or ""
        estandares.append({
            "name": x.elemento_marco,
            "codigo": em.get("codigo") or x.elemento_marco,
            "nombre": em.get("denominacion") or "",
            "nivel": nivel,
            "confirmado": bool(confirmado),
            "meta": NIVEL_META.get(nivel, _FALLBACK),
        })
    estandares.sort(key=lambda e: str(e["codigo"]))
    context.estandares = estandares

    context.resumen = {k: sum(1 for e in estandares if e["nivel"] == k) for k in ("NL", "L", "LP")}
    context.total_estandares = len(estandares)

    # --- métricas ---
    # Fase 2 (2026-07-19, hallazgo): antes eran conteos GLOBALES (institucionales)
    # mostrados en una vista de un solo programa/autoevaluación — engañoso. Ahora
    # cada uno se acota a esta AE (o a su marco/programa, donde no hay Link directo).
    context.n_criterios = _count("Valoracion Criterio", {"autoevaluacion": ae.name})
    context.n_hallazgos = _count("Hallazgo", {"autoevaluacion": ae.name})
    context.n_nc = _count("No Conformidad", {"programa_sede": ae.programa_sede}) if ae.programa_sede else _count("No Conformidad")
    context.n_planes = _count("Plan Mejora", {"autoevaluacion": ae.name})
    # Evidencia no tiene Link directo a Autoevaluacion (Trazabilidad es N:M) -> se
    # cuenta vía join: evidencias trazadas a algún Elemento Marco valorado en esta AE.
    try:
        context.n_evidencias = frappe.db.sql("""
            select count(distinct t.evidencia)
            from `tabTrazabilidad` t
            where t.elemento_marco in (
                select vc.criterio from `tabValoracion Criterio` vc where vc.autoevaluacion = %s
                union
                select ve.elemento_marco from `tabValoracion Estandar` ve where ve.autoevaluacion = %s
            )
        """, (ae.name, ae.name))[0][0] or 0
    except Exception:
        context.n_evidencias = 0
    # Indicador es el CATÁLOGO (29 institucionales) — mostrarlo sugiere medición
    # donde no la hay. Lo que corresponde en una vista de AE es cuántos de esos
    # indicadores tienen valor medido para este periodo/programa.
    context.n_indicadores = _count("Valor Indicador", {"autoevaluacion": ae.name})

    # ruta al registro en el escritorio (para editar)
    context.desk_url = "/app/autoevaluacion/" + ae.name
    return context
