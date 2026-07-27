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
- **Riesgos:** riesgos abiertos por estado y por nivel (ISO 9001 §6.1).
- **Auditoría:** auditorías por estado y hallazgos por tipo/estado (§9.2).
- **Revisión por la dirección:** estado y última revisión (§9.3).

Complementa el tablero de indicadores (M10, series de valores) y el panel
operativo de Inicio (pendientes del día). Aquí la pregunta es de gobierno:
*¿cómo va la institución?*

Nota sobre niveles: `Valoracion Estandar.nivel` es el nivel OFICIAL (Link a Nivel
Escala, permlevel 1) y solo cuenta si `confirmado`; si no, se usa
`nivel_propuesto` (Select con la sigla directa NL/L/LP) que propone el motor.

Nota sobre el nivel del riesgo: `Riesgo` NO tiene campo `nivel` — el nivel vive
en `Evaluacion Riesgo` (enlace explícito por Link `riesgo`). Se reporta el
RESIDUAL más reciente (ISO 31000: lo que queda tras el tratamiento) y, si no hay
residual, el INHERENTE más reciente. Si el riesgo no tiene ninguna evaluación con
nivel, cae en la cubeta explícita `sin_evaluar`: no se estima ni se adivina.
"""

import frappe

# Autoevaluaciones vivas (no cerradas).
_AE_ACTIVAS = ("Planificada", "En curso", "En revision", "Consolidada")
_NC_CERRADAS = ("Cerrada eficaz", "Cerrada no eficaz")
_SIGLAS = ("NL", "L", "LP")

# --- GRC (Select de los .json; nombres exactos, no inventados) ---------------
# Estados de `Riesgo`. Solo "Cerrado" es terminal: "Materializado" es el peor
# caso VIVO (es el que habilita escalar_a_no_conformidad), así que cuenta como
# abierto y además se expone aparte.
_RIESGO_ESTADOS = (
    "Identificado", "Evaluado", "En tratamiento", "Monitoreado", "Cerrado", "Materializado",
)
_RIESGO_CERRADOS = ("Cerrado",)
# Niveles de `Evaluacion Riesgo.nivel` (de menor a mayor severidad).
_RIESGO_NIVELES = ("Bajo", "Moderado", "Alto", "Extremo")
# Los que la dirección tiene que mirar hoy.
_RIESGO_NIVELES_CRITICOS = ("Alto", "Extremo")

_AUDITORIA_ESTADOS = ("Planificada", "En ejecucion", "Ejecutada", "Informe emitido", "Cerrada")
_HALLAZGO_TIPOS = (
    "No conformidad mayor", "No conformidad menor", "Observacion",
    "Oportunidad de mejora", "Conformidad", "Fortaleza",
)
_HALLAZGO_ESTADOS = ("Abierto", "Escalado a NC", "Cerrado")
_HALLAZGO_ABIERTOS = ("Abierto", "Escalado a NC")

_REVISION_ESTADOS = ("Planificada", "Realizada", "Cerrada")


def _conteo_vacio():
    return {"NL": 0, "L": 0, "LP": 0, "sin_valorar": 0}


def _por_estado(filas, campo, valores):
    """Conteo por cada valor del Select, con todos los valores presentes en cero.

    Se cuenta en Python (no N consultas): las filas ya vienen de un `get_all`.
    Un valor fuera del Select (dato viejo) se cuenta igual, sin perderse.
    """
    conteo = {v: 0 for v in valores}
    for fila in filas:
        clave = (fila.get(campo) or "").strip()
        conteo[clave] = conteo.get(clave, 0) + 1
    return conteo


@frappe.whitelist()
def resumen_ejecutivo(periodo_academico=None):
    """Payload del tablero ejecutivo. Ver docstring del módulo.

    `periodo_academico` (opcional) acota la sección de auditoría a ese Periodo
    Academico; sin él se reporta el histórico completo (comportamiento previo).
    """
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
            # OJO: son planes de mejora con semáforo rojo, NO riesgos. Los riesgos
            # del inventario GRC van en la sección `riesgos`.
            "planes_riesgo": frappe.db.count("Plan Mejora", {"semaforo": "Rojo"}),
        },
        "riesgos": seccion_riesgos(),
        "auditoria": seccion_auditoria(periodo_academico),
        "revision_direccion": seccion_revision_direccion(),
    }


# ---------------------------------------------------------------------------
# Riesgos (ISO 9001 §6.1 / ISO 31000)
# ---------------------------------------------------------------------------
def niveles_de_riesgos_abiertos():
    """Distribución por nivel de los riesgos NO cerrados.

    Devuelve ``{"Bajo": n, "Moderado": n, "Alto": n, "Extremo": n, "sin_evaluar": n}``.

    El nivel se resuelve por el enlace EXPLÍCITO `Evaluacion Riesgo.riesgo`
    (nunca por coincidencia de texto): residual más reciente y, en su defecto,
    inherente más reciente. Sin evaluación con nivel -> `sin_evaluar`.

    Es público porque el panel de Inicio (`sgc.home_dashboard`) lo reutiliza para
    su tarjeta de riesgos críticos; así la regla de resolución vive en un solo sitio.
    """
    abiertos = frappe.get_all(
        "Riesgo",
        filters={"estado": ["not in", _RIESGO_CERRADOS]},
        fields=["name"],
    )
    conteo = {n: 0 for n in _RIESGO_NIVELES}
    conteo["sin_evaluar"] = 0
    if not abiertos:
        return conteo

    nombres = [r["name"] for r in abiertos]
    # UNA sola consulta para todas las evaluaciones (evita el N+1 por riesgo).
    evaluaciones = frappe.get_all(
        "Evaluacion Riesgo",
        filters={"riesgo": ["in", nombres]},
        fields=["riesgo", "momento", "fecha", "nivel", "creation"],
    )
    # Más reciente primero. `fecha` puede venir vacía: se ordena en Python para no
    # depender de cómo el motor SQL ordena los NULL en un ORDER BY ... DESC.
    evaluaciones.sort(key=lambda e: (str(e.get("fecha") or ""), str(e.get("creation") or "")), reverse=True)

    residual, inherente = {}, {}
    for ev in evaluaciones:
        nivel = (ev.get("nivel") or "").strip()
        if nivel not in _RIESGO_NIVELES:
            continue  # evaluación sin nivel capturado: no resuelve nada
        destino = residual if ev.get("momento") == "Residual" else inherente
        destino.setdefault(ev["riesgo"], nivel)  # la primera es la más reciente

    for nombre in nombres:
        nivel = residual.get(nombre) or inherente.get(nombre)
        conteo[nivel if nivel else "sin_evaluar"] += 1
    return conteo


def seccion_riesgos():
    """Riesgos abiertos por estado y por nivel + los materializados."""
    riesgos = frappe.get_all("Riesgo", fields=["name", "estado"])
    por_estado = _por_estado(riesgos, "estado", _RIESGO_ESTADOS)
    por_nivel = niveles_de_riesgos_abiertos()
    return {
        "total": len(riesgos),
        "abiertos": sum(por_nivel.values()),
        "por_estado": por_estado,
        "por_nivel": por_nivel,
        "criticos": sum(por_nivel[n] for n in _RIESGO_NIVELES_CRITICOS),
        "materializados": por_estado.get("Materializado", 0),
        "cerrados": por_estado.get("Cerrado", 0),
    }


# ---------------------------------------------------------------------------
# Auditoría interna (ISO 9001 §9.2)
# ---------------------------------------------------------------------------
def seccion_auditoria(periodo_academico=None):
    """Auditorías por estado y sus hallazgos por tipo/estado.

    Con `periodo_academico` se filtran las auditorías de ese periodo y los
    hallazgos SOLO de esas auditorías (el hallazgo no tiene periodo propio: se
    deriva por su Link `auditoria`, no por texto).
    """
    filtros = {"periodo_academico": periodo_academico} if periodo_academico else {}
    auditorias = frappe.get_all("Auditoria", filters=filtros, fields=["name", "estado", "tipo"])

    if periodo_academico:
        nombres = [a["name"] for a in auditorias]
        hallazgos = (
            frappe.get_all(
                "Hallazgo Auditoria",
                filters={"auditoria": ["in", nombres]},
                fields=["name", "tipo", "estado"],
            )
            if nombres
            else []
        )
    else:
        hallazgos = frappe.get_all("Hallazgo Auditoria", fields=["name", "tipo", "estado"])

    hallazgos_por_estado = _por_estado(hallazgos, "estado", _HALLAZGO_ESTADOS)
    return {
        "periodo_academico": periodo_academico,
        "total": len(auditorias),
        "por_estado": _por_estado(auditorias, "estado", _AUDITORIA_ESTADOS),
        "hallazgos": {
            "total": len(hallazgos),
            "abiertos": sum(hallazgos_por_estado.get(e, 0) for e in _HALLAZGO_ABIERTOS),
            "por_tipo": _por_estado(hallazgos, "tipo", _HALLAZGO_TIPOS),
            "por_estado": hallazgos_por_estado,
        },
    }


# ---------------------------------------------------------------------------
# Revisión por la dirección (ISO 9001 §9.3)
# ---------------------------------------------------------------------------
def seccion_revision_direccion():
    """Conteo por estado y la ÚLTIMA revisión (por fecha; `creation` desempata)."""
    revisiones = frappe.get_all(
        "Revision Direccion",
        fields=["name", "codigo", "titulo", "fecha", "estado", "periodo_academico", "creation"],
    )
    # `fecha` es opcional (una revisión Planificada puede no tenerla todavía):
    # se ordena en Python igual que en los riesgos, para no depender de los NULL.
    revisiones.sort(key=lambda r: (str(r.get("fecha") or ""), str(r.get("creation") or "")), reverse=True)

    ultima = None
    if revisiones:
        u = revisiones[0]
        ultima = {
            "name": u["name"],
            "codigo": u.get("codigo"),
            "titulo": u.get("titulo"),
            "fecha": u.get("fecha"),
            "estado": u.get("estado"),
            "periodo_academico": u.get("periodo_academico"),
        }
    return {
        "total": len(revisiones),
        "por_estado": _por_estado(revisiones, "estado", _REVISION_ESTADOS),
        "ultima": ultima,
    }
