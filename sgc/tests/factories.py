# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Factories idempotentes para tests del SGC.

Construyen el dato mínimo de negocio con datos realistas, replicando el patrón
de `sgc/setup/f2_e2e_test.py`, `f3_e2e.py` y `f2_load_coneau.py` pero de forma
parametrizable y con prefijos de test.

Base del árbol (lo que casi todo test necesita)
------------------------------------------------
    crear_escala_niveles(prefijo)         -> Escala Valoracion + Nivel Escala NL/L/LP
    crear_marco_prueba(n_est, n_crit, ..) -> Marco + N Estandar x M Criterio
    crear_autoevaluacion(marco, ...)      -> Autoevaluacion ligada al marco

Valoración (dispara el motor de scoring)
----------------------------------------
    valorar_criterio(ae, criterio, cumple)          -> Valoracion Criterio (on_update -> motor)
    valorar_estandar(ae, criterios, juicios, ...)   -> [Valoracion Criterio]
    crear_valoracion_estandar(ae, est, ...)         -> Valoracion Estandar cruda (para dedup/estados)
    confirmar_estandar(ae, est, sigla)              -> fija nivel oficial + confirmado
    nivel_escala_por_sigla(sigla)                   -> name del Nivel Escala

M03 / M09 (para los agentes de esos módulos)
--------------------------------------------
    crear_proceso(...)                    -> Proceso
    crear_documento_controlado(...)       -> Documento Controlado (codigo autogenerado)
    crear_evidencia(...)                  -> Evidencia
    crear_trazabilidad(evidencia, ...)    -> Trazabilidad

Todas las factories devuelven el/los documento(s) creado(s) (frappe Document),
salvo `crear_marco_prueba` que devuelve un dict con el mapa del árbol.
"""
import itertools

import frappe

# Prefijo por defecto de todos los códigos de test (no colisiona con CONEAU-*).
PREFIJO = "TEST"

# Literales del campo Valoracion Criterio.cumple (ver scoring.py).
CUMPLE = "Cumple"
CUMPLE_PARCIAL = "Cumple parcial"   # el motor lo trata como "Cumple con debilidad" -> L
NO_CUMPLE = "No cumple"
NO_APLICA = "No aplica"

# Siglas de la escala NL/L/LP y su score/orden (score 0=NL, 1=L, 2=LP).
_NIVELES = [
    {"sigla": "NL", "etiqueta": "No logrado", "score": 0, "es_aprobatorio": 0},
    {"sigla": "L", "etiqueta": "Logrado", "score": 1, "es_aprobatorio": 1},
    {"sigla": "LP", "etiqueta": "Logrado plenamente", "score": 2, "es_aprobatorio": 1},
]

# Contador de proceso para códigos únicos dentro de una misma transacción de test.
_seq = itertools.count(1)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _insert(doctype, values):
    """Inserta un doc con permisos ignorados; devuelve el Document."""
    doc = frappe.get_doc({"doctype": doctype, **values})
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    return doc


def _ensure_named(doctype, codigo, values):
    """Idempotente para DocTypes con autoname `field:codigo`.

    Si ya existe un registro cuyo `name` == codigo, lo devuelve; si no, lo crea.
    """
    if frappe.db.exists(doctype, codigo):
        return frappe.get_doc(doctype, codigo)
    values = {"codigo": codigo, **values}
    return _insert(doctype, values)


# ---------------------------------------------------------------------------
# Escala + niveles (necesarios para confirmar `nivel` oficial NL/L/LP)
# ---------------------------------------------------------------------------
def crear_escala_niveles(prefijo=PREFIJO):
    """Crea (idempotente) la Escala Valoracion con sus 3 Nivel Escala NL/L/LP.

    `Nivel Escala` es una child table de `Escala Valoracion`; sus filas quedan
    referenciables por `name` desde el Link `Valoracion Estandar.nivel`, y
    localizables por su `sigla` (que es como las resuelven scoring/confirmacion).
    Devuelve el Document de la Escala.
    """
    codigo = f"{prefijo}-ESCALA"
    if frappe.db.exists("Escala Valoracion", codigo):
        return frappe.get_doc("Escala Valoracion", codigo)

    escala = frappe.new_doc("Escala Valoracion")
    escala.codigo = codigo
    escala.nombre = f"Escala de prueba {prefijo} NL/L/LP"
    escala.tipo = "ordinal"
    escala.min_score = 0
    escala.max_score = 2
    for n in _NIVELES:
        escala.append("niveles", {
            "codigo": n["sigla"],
            "sigla": n["sigla"],
            "etiqueta": n["etiqueta"],
            "score": n["score"],
            "orden": n["score"],
            "es_aprobatorio": n["es_aprobatorio"],
        })
    escala.flags.ignore_permissions = True
    escala.insert(ignore_permissions=True)
    return escala


def nivel_escala_por_sigla(sigla, prefijo=PREFIJO):
    """`name` del Nivel Escala cuya `sigla` == sigla (NL/L/LP). Asegura la escala."""
    crear_escala_niveles(prefijo)
    return frappe.db.get_value("Nivel Escala", {"sigla": str(sigla).strip().upper()}, "name")


# ---------------------------------------------------------------------------
# Marco Normativo + Elemento Marco (Estandar depth 2 / Criterio depth 3)
# ---------------------------------------------------------------------------
def crear_marco_prueba(n_estandares=3, n_criterios=3, prefijo=PREFIJO, con_escala=True):
    """Construye el árbol base: Marco + N Estandar, cada uno con M Criterio.

    - Marco Normativo `{prefijo}-MARCO`, ligado a la Escala NL/L/LP.
    - Estandares: Elemento Marco tipo="Estandar", is_group=1, código `{prefijo}-E{i}`.
    - Criterios:  Elemento Marco tipo="Criterio", es_valorable=1, is_group=0,
                  código `{prefijo}-E{i}-C{j}`, colgando del estándar.

    Idempotente por código. Devuelve::

        {
          "marco":       "<name del Marco>",
          "escala":      "<name de la Escala o None>",
          "estandares":  ["TEST-E1", "TEST-E2", ...],           # en orden
          "criterios":   {"TEST-E1": ["TEST-E1-C1", ...], ...}, # por estándar
        }
    """
    escala = crear_escala_niveles(prefijo) if con_escala else None

    marco_codigo = f"{prefijo}-MARCO"
    marco_vals = {
        "nombre": f"Marco de prueba {prefijo}",
        "ente": "SINEACE",
        "version": "1",
        "estado": "vigente",
    }
    if escala:
        marco_vals["escala_valoracion"] = escala.name
    marco = _ensure_named("Marco Normativo", marco_codigo, marco_vals)

    estandares = []
    criterios = {}
    for i in range(1, n_estandares + 1):
        est_cod = f"{prefijo}-E{i}"
        est = _ensure_named("Elemento Marco", est_cod, {
            "denominacion": f"Estandar de prueba {i}",
            "marco_normativo": marco.name,
            "nivel": "2",
            "tipo": "Estandar",
            "orden": i,
            "is_group": 1,
        })
        estandares.append(est.name)
        crits = []
        for j in range(1, n_criterios + 1):
            cr_cod = f"{est_cod}-C{j}"
            cr = _ensure_named("Elemento Marco", cr_cod, {
                "denominacion": f"Criterio de prueba {i}.{j}",
                "marco_normativo": marco.name,
                "nivel": "3",
                "tipo": "Criterio",
                "orden": j,
                "es_valorable": 1,
                "is_group": 0,
                "parent_elemento_marco": est.name,
            })
            crits.append(cr.name)
        criterios[est.name] = crits

    return {
        "marco": marco.name,
        "escala": escala.name if escala else None,
        "estandares": estandares,
        "criterios": criterios,
    }


# ---------------------------------------------------------------------------
# Autoevaluacion
# ---------------------------------------------------------------------------
def crear_autoevaluacion(marco, codigo=None, prefijo=PREFIJO, **extra):
    """Autoevaluacion ligada a `marco`. Código único por defecto. Devuelve el doc.

    `marco` puede ser el name del Marco Normativo o el dict devuelto por
    `crear_marco_prueba` (se toma su clave "marco").
    """
    if isinstance(marco, dict):
        marco = marco["marco"]
    if not codigo:
        codigo = f"{prefijo}-AE-{next(_seq)}"
    vals = {
        "codigo": codigo,
        "titulo": f"Autoevaluacion de prueba {codigo}",
        "marco_normativo": marco,
        # NO forzar el estado: Autoevaluacion tiene Workflow activo y setear un
        # estado != inicial ("Planificada") al insertar dispara WorkflowPermissionError.
        # El scoring no depende del estado de la autoeval. Si un test lo necesita,
        # que use frappe.model.workflow.apply_workflow.
    }
    vals.update(extra)
    return _ensure_named("Autoevaluacion", codigo, vals)


# ---------------------------------------------------------------------------
# Valoración de criterios (dispara el motor de scoring vía on_update)
# ---------------------------------------------------------------------------
def valorar_criterio(autoevaluacion, criterio, cumple=CUMPLE):
    """Inserta (o actualiza) la Valoracion Criterio de un criterio.

    Al guardar dispara `ValoracionCriterio.on_update` -> el motor recomputa el
    `nivel_propuesto` del estándar padre. Idempotente: si ya existe la valoración
    de ese (autoevaluacion, criterio), actualiza su `cumple`. Devuelve el doc.
    """
    ae = autoevaluacion.name if hasattr(autoevaluacion, "name") else autoevaluacion
    existente = frappe.db.get_value(
        "Valoracion Criterio", {"autoevaluacion": ae, "criterio": criterio}, "name"
    )
    if existente:
        vc = frappe.get_doc("Valoracion Criterio", existente)
        vc.cumple = cumple
        vc.flags.ignore_permissions = True
        vc.save(ignore_permissions=True)
        return vc
    return _insert("Valoracion Criterio", {
        "autoevaluacion": ae,
        "criterio": criterio,
        "cumple": cumple,
        "estado": "Valorado",
    })


def valorar_estandar(autoevaluacion, criterios, juicios=None, default=CUMPLE):
    """Valora todos los `criterios` de un estándar.

    - `criterios`: lista de names de criterio (p.ej. el dict["criterios"][est]).
    - `juicios`: dict {indice_0based: cumple} para sobreescribir criterios puntuales.
    - `default`: juicio para los criterios no sobreescritos.

    Ejemplo: `valorar_estandar(ae, crits, {0: "No cumple"})` -> un No cumple, resto Cumple.
    Devuelve la lista de Valoracion Criterio creadas.
    """
    juicios = juicios or {}
    docs = []
    for i, cr in enumerate(criterios):
        docs.append(valorar_criterio(autoevaluacion, cr, juicios.get(i, default)))
    return docs


# ---------------------------------------------------------------------------
# Valoracion Estandar (nivel propuesto + confirmación humana del oficial)
# ---------------------------------------------------------------------------
def crear_valoracion_estandar(autoevaluacion, estandar, nivel_propuesto=None,
                              nivel_sigla=None, confirmado=0, prefijo=PREFIJO):
    """Crea una Valoracion Estandar CRUDA (sin dedup) para un (ae, estandar).

    Útil para probar el auto-saneo de duplicados de `_upsert_valoracion_estandar`
    o para preparar estados. `nivel_sigla` (NL/L/LP) fija el `nivel` oficial
    (resuelto a Nivel Escala). Devuelve el doc.
    """
    ae = autoevaluacion.name if hasattr(autoevaluacion, "name") else autoevaluacion
    vals = {
        "autoevaluacion": ae,
        "elemento_marco": estandar,
        "confirmado": 1 if confirmado else 0,
    }
    if nivel_propuesto:
        vals["nivel_propuesto"] = nivel_propuesto
    if nivel_sigla:
        vals["nivel"] = nivel_escala_por_sigla(nivel_sigla, prefijo)
    return _insert("Valoracion Estandar", vals)


def confirmar_estandar(autoevaluacion, estandar, sigla, prefijo=PREFIJO):
    """Fija el `nivel` oficial (NL/L/LP) y `confirmado=1` de un estándar.

    Replica el estado que deja la confirmación humana, sin depender del módulo
    `confirmacion`: localiza (o crea) la Valoracion Estandar del par
    (autoevaluacion, elemento_marco) y le asigna el Nivel Escala de `sigla`.
    Devuelve el doc de Valoracion Estandar.
    """
    ae = autoevaluacion.name if hasattr(autoevaluacion, "name") else autoevaluacion
    nivel_name = nivel_escala_por_sigla(sigla, prefijo)
    name = frappe.db.get_value(
        "Valoracion Estandar", {"autoevaluacion": ae, "elemento_marco": estandar}, "name"
    )
    if name:
        ve = frappe.get_doc("Valoracion Estandar", name)
    else:
        ve = frappe.new_doc("Valoracion Estandar")
        ve.autoevaluacion = ae
        ve.elemento_marco = estandar
    ve.nivel = nivel_name
    ve.confirmado = 1
    if ve.meta.has_field("estado"):
        ve.estado = "Aprobado"
    ve.flags.ignore_permissions = True
    ve.save(ignore_permissions=True)
    return ve


# ---------------------------------------------------------------------------
# M03 — Proceso + Documento Controlado
# ---------------------------------------------------------------------------
def crear_proceso(codigo=None, prefijo=PREFIJO, **overrides):
    """Proceso mínimo (codigo autoname). Devuelve el doc."""
    if not codigo:
        # Código corto (<=12 chars) a propósito: Documento Controlado trunca el
        # proceso a 12 chars para el prefijo de su código; con "TEST-PROC-<seq>"
        # (>12 al pasar seq de 99) dos procesos truncaban al mismo prefijo y sus
        # documentos colisionaban en el PK. "TEST-P<seq>" cabe entero en 12.
        codigo = f"{prefijo}-P{next(_seq):04d}"
    vals = {"codigo": codigo}
    vals.update(overrides)
    return _ensure_named("Proceso", codigo, vals)


def crear_documento_controlado(proceso=None, tipo_documento="Procedimiento",
                               titulo=None, prefijo=PREFIJO, **overrides):
    """Documento Controlado. El `codigo` [PROC]-[SIGLA]-[NNN] lo autogenera el
    controlador en before_insert si no se pasa. Devuelve el doc.

    `proceso` puede ser un name o un doc Proceso; si es None no se liga proceso.
    """
    if hasattr(proceso, "name"):
        proceso = proceso.name
    vals = {
        "titulo": titulo or f"Documento de prueba {next(_seq)}",
        "tipo_documento": tipo_documento,
    }
    if proceso:
        vals["proceso"] = proceso
    vals.update(overrides)
    return _insert("Documento Controlado", vals)


# ---------------------------------------------------------------------------
# M09 — Evidencia + Trazabilidad
# ---------------------------------------------------------------------------
def crear_evidencia(codigo=None, titulo=None, tipo="Enlace",
                    enlace_url=None, prefijo=PREFIJO, **overrides):
    """Evidencia mínima. Por defecto tipo="Enlace" con un `enlace_url` como soporte:
    M09 (_validar_soporte) solo acepta enlace_url cuando tipo=="Enlace"; para otros
    tipos exige `archivo`. Devuelve el doc.
    """
    if not codigo:
        codigo = f"{prefijo}-EVD-{next(_seq)}"
    vals = {
        "codigo": codigo,
        "titulo": titulo or f"Evidencia de prueba {codigo}",
        "tipo": tipo,
    }
    # Soporte por defecto (url) salvo que el caller lo maneje explícitamente.
    if enlace_url is not None or "archivo" not in overrides:
        vals["enlace_url"] = enlace_url or "https://example.test/evidencia"
    vals.update(overrides)
    return _ensure_named("Evidencia", codigo, vals)


def crear_trazabilidad(evidencia, elemento_marco=None, proceso=None,
                       tipo_vinculo="Cumple", **overrides):
    """Trazabilidad que liga una Evidencia a un elemento_marco o proceso.

    M09 exige que al menos uno de (elemento_marco, proceso) esté presente.
    Devuelve el doc.
    """
    ev = evidencia.name if hasattr(evidencia, "name") else evidencia
    vals = {
        "evidencia": ev,
        "tipo_vinculo": tipo_vinculo,
    }
    if elemento_marco:
        vals["elemento_marco"] = elemento_marco
    if proceso:
        vals["proceso"] = proceso
    vals.update(overrides)
    return _insert("Trazabilidad", vals)


# ---------------------------------------------------------------------------
# M12 — Encuestas a grupos de interés
# ---------------------------------------------------------------------------
def crear_grupo_interes(codigo=None, nombre=None, tipo="Beneficiario",
                        prefijo=PREFIJO, **overrides):
    """Grupo Interes (autoname field:codigo). Idempotente por código. Devuelve el doc."""
    if not codigo:
        codigo = f"{prefijo}-GI-{next(_seq)}"
    vals = {
        "nombre": nombre or f"Grupo de interés {codigo}",
        "tipo": tipo,
    }
    vals.update(overrides)
    return _ensure_named("Grupo Interes", codigo, vals)


def crear_instrumento(codigo=None, nombre=None, tipo="Encuesta satisfacción",
                      plataforma="Otra", grupo_interes=None, prefijo=PREFIJO,
                      **overrides):
    """Instrumento (autoname field:codigo). Idempotente por código. Devuelve el doc.

    `plataforma` por defecto "Otra" para no exigir survey_id (LimeSurvey solo
    emite un msgprint si falta, no bloquea, pero "Otra" mantiene los tests limpios).
    `grupo_interes` puede ser un name o un doc Grupo Interes.
    """
    if not codigo:
        codigo = f"{prefijo}-INS-{next(_seq)}"
    if hasattr(grupo_interes, "name"):
        grupo_interes = grupo_interes.name
    vals = {
        "nombre": nombre or f"Instrumento {codigo}",
        "tipo": tipo,
        "plataforma": plataforma,
    }
    if grupo_interes:
        vals["grupo_interes"] = grupo_interes
    vals.update(overrides)
    return _ensure_named("Instrumento", codigo, vals)


def crear_aplicacion_instrumento(instrumento=None, prefijo=PREFIJO, **overrides):
    """Aplicacion Instrumento (autoname format:APL-{YYYY}-{#####}). Devuelve el doc.

    Crea un Instrumento mínimo si no se pasa. `instrumento` puede ser name o doc.
    NO fija estado != inicial ("Planificada") por defecto: el DocType tiene
    Workflow y hacerlo dispararía WorkflowPermissionError salvo que el test lo
    haya desactivado con `desactivar_workflow("Aplicacion Instrumento")`.
    """
    if instrumento is None:
        instrumento = crear_instrumento(prefijo=prefijo).name
    elif hasattr(instrumento, "name"):
        instrumento = instrumento.name
    vals = {"instrumento": instrumento}
    vals.update(overrides)
    return _insert("Aplicacion Instrumento", vals)


def crear_resultado_instrumento(aplicacion, dimension=None, valor=None,
                                unidad=None, n=None, prefijo=PREFIJO, **overrides):
    """Resultado Instrumento (autoname format:RES-{YYYY}-{#####}). Devuelve el doc.

    `aplicacion` puede ser un name o un doc Aplicacion Instrumento.
    """
    ap = aplicacion.name if hasattr(aplicacion, "name") else aplicacion
    vals = {"aplicacion_instrumento": ap}
    if dimension is not None:
        vals["dimension"] = dimension
    if valor is not None:
        vals["valor"] = valor
    if unidad is not None:
        vals["unidad"] = unidad
    if n is not None:
        vals["n"] = n
    vals.update(overrides)
    return _insert("Resultado Instrumento", vals)


def desactivar_workflow(document_type):
    """Desactiva (is_active=0) el Workflow de un DocType durante los tests.

    Autoevaluacion y No Conformidad tienen Workflow activo: setear un estado
    != inicial dispara WorkflowPermissionError. Los tests que ejercitan las
    validaciones del CONTROLADOR por estado (validate) necesitan mover el estado
    libremente; el workflow se reactiva solo entre casos por el rollback, pero
    llamar esto en setUp lo desactiva para el caso. No toca la logica de validate.
    """
    nombres = frappe.get_all(
        "Workflow", filters={"document_type": document_type, "is_active": 1}, pluck="name"
    )
    for n in nombres:
        frappe.db.set_value("Workflow", n, "is_active", 0)
    # Limpiar el cache de workflow para que el cambio surta efecto en el mismo request.
    frappe.clear_cache(doctype=document_type)
