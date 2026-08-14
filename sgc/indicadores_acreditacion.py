# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Indicadores de acreditación medidos — motor lector para las vistas.

Responde una sola pregunta: **qué indicadores del marco de acreditación tienen
medición para una autoevaluación concreta, y qué dice esa medición**.

Es el consumidor de lo que producen los conectores externos (un Data Warehouse
institucional, un ETL de la base académica, una encuesta cerrada): todos
escriben en `Valor Indicador` y se distinguen entre sí por el campo `fuente`.

    conector externo → Valor Indicador (fuente=X, programa_sede, periodo)
                     → esta vista, resuelta contra la Autoevaluacion

Cuatro reglas de diseño, ninguna accidental:

1. **El enganche se resuelve por (programa_sede, periodo_academico), NO por el
   campo `autoevaluacion`.** Un conector externo publica una medición de un
   programa en un periodo; que esa medición se enganche o no al expediente
   formal de una autoevaluación es una decisión del proceso de Calidad, no del
   conector ni de esta vista. Leer por el par permite MOSTRAR el dato sin
   TOMAR esa decisión por ellos. Si algún día Calidad decide poblar
   `autoevaluacion`, esta función sigue funcionando igual.

2. **Nunca se mezclan fuentes en una misma cifra.** Varios productores pueden
   publicar el MISMO indicador con valores distintos (universos y reglas de
   cálculo distintos). Un panel que sume o promedie entre fuentes muestra una
   cifra que no existe en ninguna. Por eso se lee UNA fuente a la vez, y
   `otras_fuentes()` reporta el resto para que la UI lo advierta en vez de
   ocultarlo.

3. **Nunca se mezclan granos de desagregación.** Un mismo indicador puede estar
   publicado a nivel institucional, por sede y por programa-sede. Se lee solo
   el grano del programa de la autoevaluación; agregarle el institucional
   produciría dos filas del mismo indicador con cifras legítimamente distintas.

4. **Nunca se infiere el cumplimiento.** Si el productor declaró en el texto si
   la medición cumple la meta, se respeta; si no lo declaró, queda en `None` y
   la UI lo muestra neutro. Recalcularlo aquí exigiría asumir el sentido de la
   comparación (≥ o ≤) y el redondeo, que son del productor, no de la vista.

El campo `valor_texto` es prosa libre en el doctype, pero los conectores lo
escriben con una convención estable de la que se extraen los metadatos:

    <origen> · n=<denominador> · meta <X>% (cumple|NO cumple)[ · PROVISIONAL (cobertura <N>%)]

`_parsear_valor_texto()` la lee de forma tolerante: lo que reconoce lo estructura
y lo que no, lo deja crudo en `texto` con `contrato_reconocido=False`. Un cambio
de formato del productor degrada la presentación, nunca rompe la página.
"""

import re

import frappe

# Fuente por defecto de los indicadores calculados. Es un DEFAULT, no una
# constante de negocio: cada institución nombra a su productor como quiera y lo
# fija con `frappe.db.set_default("sgc_fuente_indicadores", "<nombre>")` sin
# tocar código (mismo mecanismo que el default `company` que usa el informe).
FUENTE_POR_DEFECTO = "dw"
CLAVE_DEFAULT_FUENTE = "sgc_fuente_indicadores"

# Razones por las que no hay filas que mostrar (contrato estable para la UI).
SIN_PROGRAMA = "autoevaluacion_sin_programa_sede"
SIN_PERIODO = "autoevaluacion_sin_periodo"
SIN_MEDICIONES = "sin_mediciones_para_el_par"

_RE_N = re.compile(r"\bn\s*=\s*([\d.,]+)", re.IGNORECASE)
# La meta puede venir con operador ("meta ≥ 80%") o sin él ("meta 80 %"). El
# símbolo se captura en vez de descartarse: si el productor escribió "%", la
# meta es un porcentaje según ÉL, y eso vale más que deducirlo aquí.
_RE_META = re.compile(r"\bmeta\s*([<>≥≤]?\s*=?)\s*(-?[\d.,]+)\s*(%?)", re.IGNORECASE)
_RE_COBERTURA = re.compile(r"\bcobertura\s*(-?[\d.,]+)\s*%?", re.IGNORECASE)
_RE_NO_CUMPLE = re.compile(r"\bno\s+cumple\b", re.IGNORECASE)
_RE_CUMPLE = re.compile(r"\bcumple\b", re.IGNORECASE)
_RE_PROVISIONAL = re.compile(r"\bprovisional\b", re.IGNORECASE)
# El productor declara contra qué norma juzga: "…v1-norma Coneau 2026 · n=…".
# Importa mostrarlo: el MISMO valor puede cumplir un marco y no otro, porque los
# umbrales los fija cada régimen. Un "no cumple" sin marco se lee como
# incumplimiento legal cuando puede ser solo "no alcanza un sello voluntario".
_RE_MARCO = re.compile(r"\bnorma\s+([^·\n]+)", re.IGNORECASE)

# Separa un código en (prefijo, número) para ordenarlo como lo lee una persona:
# ID6 antes que ID10, y ambos antes que INST-ID11.
_RE_CODIGO = re.compile(r"^(.*?)(\d+)\s*$")


def fuente_preferida():
    """Nombre del productor que las vistas muestran por defecto."""
    return frappe.db.get_default(CLAVE_DEFAULT_FUENTE) or FUENTE_POR_DEFECTO


def _num(texto):
    """Convierte el número de un match a float, tolerando coma decimal."""
    try:
        return float(str(texto).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def _parsear_valor_texto(texto):
    """Extrae los metadatos de la convención del productor.

    Devuelve siempre el mismo dict; `contrato_reconocido` dice si se pudo leer
    algo estructurado. Nunca lanza: `valor_texto` es prosa libre y un productor
    nuevo (o una edición a mano) no debe tumbar la página que lo muestra.
    """
    crudo = (texto or "").strip()
    meta = {
        "texto": crudo,
        "n": None,
        "meta": None,
        "meta_operador": "",
        "meta_sufijo": "",
        "cumple": None,
        "marco": "",
        "provisional": False,
        "cobertura": None,
        "contrato_reconocido": False,
    }
    if not crudo:
        return meta

    m = _RE_MARCO.search(crudo)
    if m:
        meta["marco"] = m.group(1).strip()

    m = _RE_N.search(crudo)
    if m:
        meta["n"] = _num(m.group(1))

    m = _RE_META.search(crudo)
    if m:
        meta["meta"] = _num(m.group(2))
        meta["meta_operador"] = (m.group(1) or "").replace(" ", "")
        meta["meta_sufijo"] = m.group(3) or ""

    # "NO cumple" contiene "cumple": se descarta primero el negativo, si no
    # cualquier incumplimiento se leería como cumplimiento.
    if _RE_NO_CUMPLE.search(crudo):
        meta["cumple"] = False
    elif _RE_CUMPLE.search(crudo):
        meta["cumple"] = True

    if _RE_PROVISIONAL.search(crudo):
        meta["provisional"] = True
        m = _RE_COBERTURA.search(crudo)
        if m:
            meta["cobertura"] = _num(m.group(1))

    meta["contrato_reconocido"] = any((
        meta["n"] is not None,
        meta["meta"] is not None,
        meta["cumple"] is not None,
        meta["provisional"],
        bool(meta["marco"]),
    ))
    return meta


def _sufijo_de_unidad(unidad):
    """Símbolo corto para pegar al número, o "" si la unidad no es pegable.

    `Ficha Indicador.unidad` es texto libre: unas fichas escriben "%", otras
    "Porcentaje", otras "Docentes a tiempo completo". Solo lo corto se pega al
    valor; lo demás se muestra aparte para no ensuciar la cifra.
    """
    u = (unidad or "").strip()
    if not u:
        return ""
    if "%" in u or u.lower().startswith("porcentaje"):
        return "%"
    return u if len(u) <= 3 else ""


def _orden_codigo(codigo):
    """Clave de orden natural: ('ID', 6) < ('ID', 10) < ('INST-ID', 11)."""
    m = _RE_CODIGO.match(str(codigo or ""))
    if not m:
        return (str(codigo or ""), 0)
    return (m.group(1), int(m.group(2)))


def _par_de_autoevaluacion(autoevaluacion):
    """(programa_sede, periodo_academico) de la AE, o None si falta alguno."""
    return frappe.db.get_value(
        "Autoevaluacion",
        autoevaluacion,
        ["programa_sede", "periodo_academico"],
        as_dict=True,
    )


def indicadores_de_autoevaluacion(autoevaluacion, fuente=None):
    """Indicadores medidos para el programa y periodo de una autoevaluación.

    `fuente` acota a UN productor (por defecto, el preferido de la institución).

    Devuelve `{"fuente", "filas", "motivo"}`. `filas` trae una fila por
    indicador —la medición más reciente, si el productor publicó varias— con el
    valor, el nombre legible del indicador y los metadatos parseados del texto.
    `motivo` explica por qué `filas` viene vacía, para que la UI diga algo mejor
    que un espacio en blanco.
    """
    fuente = fuente or fuente_preferida()
    vacio = {"fuente": fuente, "filas": [], "motivo": None}

    par = _par_de_autoevaluacion(autoevaluacion)
    if not par or not par.get("programa_sede"):
        return {**vacio, "motivo": SIN_PROGRAMA}
    if not par.get("periodo_academico"):
        return {**vacio, "motivo": SIN_PERIODO}

    valores = frappe.get_all(
        "Valor Indicador",
        filters={
            "programa_sede": par["programa_sede"],
            "periodo_academico": par["periodo_academico"],
            "fuente": fuente,
        },
        fields=["name", "indicador", "valor_num", "valor_texto", "fecha", "calculado"],
        # Más reciente primero: `fecha` es opcional, así que `creation` desempata.
        order_by="fecha desc, creation desc",
    )
    if not valores:
        return {**vacio, "motivo": SIN_MEDICIONES}

    # Una fila por indicador: la primera que aparece es la más reciente.
    vistos = {}
    for v in valores:
        vistos.setdefault(v.indicador, v)

    nombres = _nombres_de_indicador(list(vistos))
    unidades = _unidades_de_indicador(list(vistos))

    filas = [
        {
            "name": v.name,
            "indicador": codigo,
            "nombre": nombres.get(codigo, ""),
            "unidad": unidades.get(codigo, ""),
            "sufijo": _sufijo_de_unidad(unidades.get(codigo, "")),
            "valor_num": v.valor_num,
            "calculado": bool(v.calculado),
            "fecha": v.fecha,
            **_parsear_valor_texto(v.valor_texto),
        }
        for codigo, v in vistos.items()
    ]
    filas.sort(key=lambda f: _orden_codigo(f["indicador"]))
    return {"fuente": fuente, "filas": filas, "motivo": None}


def _nombres_de_indicador(codigos):
    """Mapa {codigo: nombre legible} en una consulta."""
    if not codigos:
        return {}
    filas = frappe.get_all(
        "Indicador",
        filters={"name": ["in", codigos]},
        fields=["name", "nombre"],
    )
    return {f["name"]: f["nombre"] or "" for f in filas}


def _unidades_de_indicador(codigos):
    """Mapa {codigo: unidad} desde `Ficha Indicador` (1:1 con el indicador).

    La unidad es del catálogo, no de la medición: el conector publica un número
    y la ficha dice si eso es un porcentaje, un conteo o una razón. Sin ficha se
    devuelve cadena vacía y la vista muestra el número desnudo, que es la
    lectura honesta cuando nadie declaró en qué se mide.
    """
    if not codigos:
        return {}
    filas = frappe.get_all(
        "Ficha Indicador",
        filters={"indicador": ["in", codigos]},
        fields=["indicador", "unidad"],
    )
    return {f["indicador"]: (f["unidad"] or "").strip() for f in filas}


def otras_fuentes(autoevaluacion, excepto=None):
    """Otros productores con mediciones para el mismo programa y periodo.

    Existe para que la vista pueda ADVERTIR que hay más de una cifra publicada
    del mismo indicador en vez de elegir una en silencio. Devuelve
    `[{"fuente", "n_indicadores"}]`, sin la fuente que se está mostrando.
    """
    excepto = excepto or fuente_preferida()
    par = _par_de_autoevaluacion(autoevaluacion)
    if not par or not par.get("programa_sede") or not par.get("periodo_academico"):
        return []

    valores = frappe.get_all(
        "Valor Indicador",
        filters={
            "programa_sede": par["programa_sede"],
            "periodo_academico": par["periodo_academico"],
        },
        fields=["fuente", "indicador"],
    )
    conteo = {}
    for v in valores:
        # Un productor que no se identificó no es comparable con los que sí:
        # se agrupa como "sin fuente" en vez de descartarlo en silencio.
        nombre = (v.fuente or "").strip() or "(sin fuente)"
        if nombre == excepto:
            continue
        conteo.setdefault(nombre, set()).add(v.indicador)

    return [
        {"fuente": f, "n_indicadores": len(inds)}
        for f, inds in sorted(conteo.items())
    ]


def contar_indicadores_medidos(autoevaluacion):
    """Cuántos indicadores DISTINTOS tienen alguna medición para esta AE.

    Cuenta indicadores, no registros, y a través de todas las fuentes: dos
    productores midiendo el mismo indicador siguen siendo un solo indicador
    medido. Es el número que corresponde a un contador de portada; el detalle
    por fuente lo da `indicadores_de_autoevaluacion()`.
    """
    par = _par_de_autoevaluacion(autoevaluacion)
    if not par or not par.get("programa_sede") or not par.get("periodo_academico"):
        return 0

    valores = frappe.get_all(
        "Valor Indicador",
        filters={
            "programa_sede": par["programa_sede"],
            "periodo_academico": par["periodo_academico"],
        },
        fields=["indicador"],
        distinct=True,
    )
    return len({v.indicador for v in valores})
