"""Flujo CAPA del SGC (F2 §4) — Hallazgo -> No Conformidad -> Plan Mejora.

Reutiliza el CAPA de F1 (Hallazgo / Plan Mejora / Accion Mejora): NO duplica
entidades. El motor de mejora es unico (ISO 9001 §10) y la No Conformidad tiene
origen polimorfico (origen_doctype / origen_id / origen_tipo).

Nombres de campo y valores de Select tomados de los .json REALES:
- Valoracion Criterio: cumple = `Cumple | Cumple parcial | No cumple | No aplica`
  (el contrato hablaba de "Cumple con debilidad"; el Select real usa
   "Cumple parcial" -> se ADAPTA a ese valor). El sustento cualitativo esta en
   `observacion` (no existe `debilidad`). El criterio es `criterio` (link Elemento Marco).
- Hallazgo: tipo = `Fortaleza | Debilidad | Oportunidad de mejora`;
  origen = `Autoevaluacion | Auditoria | Supervision`; `codigo` reqd+unique;
  campos `criterio`, `autoevaluacion`, `programa_sede`, `descripcion`,
  `no_conformidad`, `escalado_a_nc`.
- No Conformidad: `titulo` reqd; `origen_doctype` (Link DocType),
  `origen_id` (Dynamic Link), `origen_tipo` (Select, incluye `Autoevaluacion`),
  `tipo` (`No conformidad mayor|menor|Observacion|Oportunidad de mejora`),
  `descripcion`, `criterio`, `programa_sede`, `unidad_organica`, `plan_mejora`.
- Plan Mejora: `codigo` reqd+unique; `titulo`; origen polimorfico
  (`origen_doctype`/`origen_id`); `autoevaluacion`; estado `Borrador|En ejecucion|Cerrado`.
- Accion Mejora: `codigo` reqd+unique; `plan_mejora`, `no_conformidad`, `hallazgo`,
  `criterio`, `descripcion`, `tipo` (`Correctiva|Preventiva|Mejora`).

Uso programatico:
    from sgc.capa import generar_hallazgo, escalar_a_no_conformidad, crear_plan
"""
import frappe

# Valores de Valoracion Criterio.cumple que disparan un hallazgo (adaptados al Select real).
CUMPLE_DISPARA_HALLAZGO = ("No cumple", "Cumple parcial")


# ---------------------------------------------------------------------------
# Helpers de naming (los DocTypes CAPA usan autoname field:codigo -> generamos codigo)
# ---------------------------------------------------------------------------
def _next_codigo(doctype, prefix):
    """Genera un codigo secuencial simple prefix-YYYY-#### unico por DocType.
    Idempotencia real la dan los buscadores de cada funcion; esto solo evita choques.
    """
    year = frappe.utils.nowdate()[:4]
    like = f"{prefix}-{year}-%"
    n = frappe.db.count(doctype, {"codigo": ["like", like]})
    # reintenta hasta encontrar hueco (por si hubo borrados)
    while True:
        n += 1
        codigo = f"{prefix}-{year}-{n:04d}"
        if not frappe.db.exists(doctype, {"codigo": codigo}):
            return codigo


# ---------------------------------------------------------------------------
# 1) generar_hallazgo
# ---------------------------------------------------------------------------
def generar_hallazgo(valoracion_criterio_name):
    """Crea un Hallazgo (cualitativo de autoevaluacion) a partir de una
    Valoracion Criterio con `cumple in (No cumple, Cumple parcial)`.

    - tipo: `Debilidad` si `No cumple`; `Oportunidad de mejora` si `Cumple parcial`.
    - link a `criterio` (Elemento Marco), `autoevaluacion`, y `programa_sede`
      derivado de la Autoevaluacion.
    - descripcion: copiada de `observacion` de la valoracion.
    Idempotente: si ya existe un Hallazgo (origen=Autoevaluacion) para esa
    misma autoevaluacion + criterio, lo devuelve sin duplicar.

    Devuelve el doc Hallazgo, o None si la valoracion no dispara hallazgo.
    """
    vc = frappe.get_doc("Valoracion Criterio", valoracion_criterio_name)

    if vc.cumple not in CUMPLE_DISPARA_HALLAZGO:
        return None

    # deriva programa_sede desde la autoevaluacion
    programa_sede = frappe.db.get_value(
        "Autoevaluacion", vc.autoevaluacion, "programa_sede"
    )

    # idempotencia: hallazgo existente para misma autoeval + criterio + origen autoeval
    existente = frappe.db.get_value(
        "Hallazgo",
        {
            "origen": "Autoevaluacion",
            "autoevaluacion": vc.autoevaluacion,
            "criterio": vc.criterio,
        },
        "name",
    )
    if existente:
        return frappe.get_doc("Hallazgo", existente)

    tipo = "Debilidad" if vc.cumple == "No cumple" else "Oportunidad de mejora"

    hallazgo = frappe.get_doc({
        "doctype": "Hallazgo",
        "codigo": _next_codigo("Hallazgo", "HALL"),
        "tipo": tipo,
        "origen": "Autoevaluacion",
        "criterio": vc.criterio,
        "autoevaluacion": vc.autoevaluacion,
        "programa_sede": programa_sede,
        "descripcion": vc.observacion or "",
        "estado": "Abierto",
        "fecha": frappe.utils.nowdate(),
    }).insert(ignore_permissions=True)

    return hallazgo


# ---------------------------------------------------------------------------
# 2) escalar_a_no_conformidad
# ---------------------------------------------------------------------------
def escalar_a_no_conformidad(hallazgo_name):
    """Escala un Hallazgo a No Conformidad (origen polimorfico Autoevaluacion).

    - origen_doctype="Autoevaluacion", origen_id=la autoevaluacion del hallazgo,
      origen_tipo="Autoevaluacion".
    - copia criterio / programa_sede / unidad_organica.
    - setea hallazgo.no_conformidad y hallazgo.escalado_a_nc=1.
    Idempotente: si el hallazgo ya tiene `no_conformidad`, devuelve esa NC.

    Devuelve el doc No Conformidad.
    """
    hallazgo = frappe.get_doc("Hallazgo", hallazgo_name)

    if hallazgo.no_conformidad:
        return frappe.get_doc("No Conformidad", hallazgo.no_conformidad)

    # tipo de NC segun el tipo de hallazgo
    tipo_nc = (
        "Oportunidad de mejora"
        if hallazgo.tipo == "Oportunidad de mejora"
        else "No conformidad menor"
    )

    titulo = f"NC desde hallazgo {hallazgo.codigo}"
    if hallazgo.criterio:
        titulo = f"NC criterio {hallazgo.criterio} ({hallazgo.codigo})"

    nc = frappe.get_doc({
        "doctype": "No Conformidad",
        "titulo": titulo,
        "origen_doctype": "Autoevaluacion",
        "origen_id": hallazgo.autoevaluacion,
        "origen_tipo": "Autoevaluacion",
        "tipo": tipo_nc,
        "descripcion": hallazgo.descripcion or "",
        "criterio": hallazgo.criterio,
        "programa_sede": hallazgo.programa_sede,
        "unidad_organica": hallazgo.unidad_organica,
        "estado": "Abierta",
        "requiere_analisis_causa": 1,
        "fecha_deteccion": frappe.utils.nowdate(),
    }).insert(ignore_permissions=True)

    # marca el hallazgo como escalado
    hallazgo.no_conformidad = nc.name
    hallazgo.escalado_a_nc = 1
    hallazgo.save(ignore_permissions=True)

    return nc


# ---------------------------------------------------------------------------
# 3) crear_plan
# ---------------------------------------------------------------------------
def crear_plan(no_conformidad_name, crear_accion_ejemplo=False):
    """Crea un Plan Mejora (origen polimorfico No Conformidad) enlazado a la NC,
    y setea nc.plan_mejora. Idempotente: si la NC ya tiene `plan_mejora`, lo devuelve.

    Si `crear_accion_ejemplo=True`, agrega una Accion Mejora inicial ligada al plan
    y a la NC (tipo Correctiva).

    Devuelve el doc Plan Mejora.
    """
    nc = frappe.get_doc("No Conformidad", no_conformidad_name)

    if nc.plan_mejora:
        return frappe.get_doc("Plan Mejora", nc.plan_mejora)

    plan = frappe.get_doc({
        "doctype": "Plan Mejora",
        "codigo": _next_codigo("Plan Mejora", "PM"),
        "titulo": f"Plan de mejora para {nc.titulo}",
        "origen_doctype": "No Conformidad",
        "origen_id": nc.name,
        # si la NC vino de una autoevaluacion, se cosecha ese enlace para reportes
        "autoevaluacion": (
            nc.origen_id if nc.origen_doctype == "Autoevaluacion" else None
        ),
        "unidad_organica": nc.unidad_organica,
        "estado": "Borrador",
    }).insert(ignore_permissions=True)

    # enlaza la NC al plan
    nc.plan_mejora = plan.name
    nc.save(ignore_permissions=True)

    if crear_accion_ejemplo:
        frappe.get_doc({
            "doctype": "Accion Mejora",
            "codigo": _next_codigo("Accion Mejora", "AM"),
            "plan_mejora": plan.name,
            "no_conformidad": nc.name,
            "criterio": nc.criterio,
            "descripcion": "Accion correctiva inicial (definir por el responsable).",
            "tipo": "Correctiva",
            "estado": "Planificada",
            "avance_pct": 0,
        }).insert(ignore_permissions=True)

    return plan
