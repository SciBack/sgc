# Copyright (c) 2026, SciBack and Contributors
# For license information, please see license.txt

"""M13 — Tablero ejecutivo de acreditación.

Vista institucional (dirección de calidad / autoridades): cómo va la acreditación
en TODOS los programas, no en uno. Responde de un vistazo:

- **Cobertura:** cuántos programas tienen autoevaluación iniciada del total.
- **Por programa:** avance, estado y distribución de niveles de sus estándares.
- **Distribución institucional:** cuántos estándares NL / L / LP (y sin valorar).
- **CBC:** semáforo y conteos del último informe de cumplimiento.
- **Mejora:** no conformidades abiertas y planes en riesgo.

Complementa el tablero de indicadores (M10, series de valores) y el panel
operativo de Inicio (pendientes del día). Aquí la pregunta es de gobierno:
*¿cómo va la institución?*

Nota sobre niveles: `Valoracion Estandar.nivel` es el nivel OFICIAL (Link a Nivel
Escala, permlevel 1) y solo cuenta si `confirmado`; si no, se usa
`nivel_propuesto` (Select con la sigla directa NL/L/LP) que propone el motor.
"""

import frappe

# Autoevaluaciones vivas (no cerradas).
_AE_ACTIVAS = ("Planificada", "En curso", "En revision", "Consolidada")
_NC_CERRADAS = ("Cerrada eficaz", "Cerrada no eficaz")
_SIGLAS = ("NL", "L", "LP")


def _conteo_vacio():
    return {"NL": 0, "L": 0, "LP": 0, "sin_valorar": 0}


@frappe.whitelist()
def resumen_ejecutivo():
    """Payload del tablero ejecutivo. Ver docstring del módulo."""
    programas_total = frappe.db.count("Programa Sede")
    aes = frappe.get_all(
        "Autoevaluacion",
        filters={"estado": ["in", _AE_ACTIVAS]},
        fields=[
            "name", "titulo", "programa_sede", "periodo_academico",
            "marco_normativo", "estado", "avance_pct", "resultado_vigencia",
        ],
        order_by="modified desc",
    )

    institucional = _conteo_vacio()
    sigla_cache = {}

    def _sigla_oficial(nivel_name):
        if not nivel_name:
            return None
        if nivel_name not in sigla_cache:
            sigla_cache[nivel_name] = frappe.db.get_value("Nivel Escala", nivel_name, "sigla")
        return sigla_cache[nivel_name]

    for ae in aes:
        valoraciones = frappe.get_all(
            "Valoracion Estandar",
            filters={"autoevaluacion": ae["name"]},
            fields=["nivel", "nivel_propuesto", "confirmado"],
        )
        conteo = _conteo_vacio()
        for v in valoraciones:
            if v.get("confirmado") and v.get("nivel"):
                sigla = _sigla_oficial(v["nivel"])
            else:
                sigla = v.get("nivel_propuesto")
            sigla = (sigla or "").strip().upper()
            if sigla in _SIGLAS:
                conteo[sigla] += 1
            else:
                conteo["sin_valorar"] += 1

        for clave, valor in conteo.items():
            institucional[clave] += valor

        ae["niveles"] = conteo
        ae["estandares_total"] = len(valoraciones)

    iac = frappe.get_all(
        "Informe Cumplimiento",
        fields=["name", "anio", "semaforo", "n_cumple", "n_parcial", "n_no_cumple"],
        order_by="anio desc",
        limit=1,
    )

    return {
        "cobertura": {
            "programas_total": programas_total,
            "con_autoevaluacion": len(aes),
            "pct": round(len(aes) * 100 / programas_total) if programas_total else 0,
        },
        "programas": aes,
        "niveles": institucional,
        "cbc": iac[0] if iac else None,
        "mejora": {
            "nc_abiertas": frappe.db.count("No Conformidad", {"estado": ["not in", _NC_CERRADAS]}),
            "planes_riesgo": frappe.db.count("Plan Mejora", {"semaforo": "Rojo"}),
        },
    }
