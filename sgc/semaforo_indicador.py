"""Semáforo de cumplimiento de un indicador (issue #31).

Un indicador sin meta no se puede evaluar: se puede registrar su valor, pero no
decir si ese valor está bien o mal. Esto calcula ese juicio a partir de lo que la
`Ficha Indicador` declara.

## Por qué no hay un DocType de meta

La revisión de arquitectura del 20-sep-2026 descartó crear `Meta Indicador`: la
semántica de meta **ya existía** en la ficha (`valor_referencial`, descrito como
«Umbral (ID1 ≥ 60%)», y `margen_error`, «±3% por defecto (escala oficial §9.1)»).
Añadir un DocType aparte habría dejado dos sitios respondiendo a «¿cuál es el
objetivo de este indicador?», con el semáforo calculando contra uno y la
acreditación evaluándose contra el otro.

## Las dos formas de tener razón

No todos los indicadores se evalúan igual, y confundirlo invierte el resultado:

* **Umbral fijo** — se compara contra `valor_referencial`. Y el `sentido` decide
  de qué lado está lo bueno: en una tasa de graduación más es mejor; en una de
  deserción, al revés. Sin declararlo, la mitad del catálogo saldría al revés.
* **Evolución** — no hay número que alcanzar: basta con mejorar respecto al
  periodo anterior. Este modo explicita lo que la ficha insinuaba con el campo
  `regla_evolucion` («Si aplica evolución positiva n-1→n como aceptable»).

## La zona ámbar

`margen_error` se interpreta como **porcentaje del umbral**, coherente con su
descripción («±3%»). Quedar dentro de ese margen no es cumplir, pero tampoco es
fallar: es ámbar. Sin margen declarado no hay ámbar, solo verde o rojo.

## Cuando no se puede juzgar, no se juzga

Sin ficha, sin meta declarada o sin periodo anterior con el que comparar, el
semáforo queda **vacío**. No se inventa un color: un verde falso es peor que un
hueco, porque nadie revisa lo que parece estar bien.
"""
import frappe
from frappe.utils import flt

VERDE = "Verde"
AMBAR = "Ambar"
ROJO = "Rojo"

MODO_UMBRAL = "Umbral fijo"
MODO_EVOLUCION = "Evolucion respecto al periodo anterior"

MAYOR_MEJOR = "Mayor es mejor"
MENOR_MEJOR = "Menor es mejor"


def _ficha(indicador):
    """La ficha del indicador. `Ficha Indicador.indicador` es unique: hay una o ninguna."""
    if not indicador:
        return None
    nombre = frappe.db.get_value("Ficha Indicador", {"indicador": indicador}, "name")
    return frappe.get_cached_doc("Ficha Indicador", nombre) if nombre else None


def _modo(ficha):
    """El modo declarado; si no se declaró, se deriva del campo antiguo.

    Las fichas creadas antes de este cambio no tienen `modo_evaluacion`, pero
    muchas sí tienen `regla_evolucion` marcado. Derivarlo evita una migración y,
    sobre todo, evita que esas fichas pasen a evaluarse contra un umbral cuando
    su autor había dicho que se evaluaban por evolución.
    """
    declarado = (ficha.get("modo_evaluacion") or "").strip()
    if declarado:
        return declarado
    return MODO_EVOLUCION if ficha.get("regla_evolucion") else MODO_UMBRAL


def _por_umbral(valor, umbral, sentido, margen_pct):
    """Verde si cumple; ámbar si falla dentro del margen; rojo si falla fuera."""
    holgura = abs(flt(umbral) * flt(margen_pct) / 100.0) if margen_pct else 0.0

    if sentido == MENOR_MEJOR:
        if valor <= umbral:
            return VERDE
        return AMBAR if valor <= umbral + holgura else ROJO

    if valor >= umbral:
        return VERDE
    return AMBAR if valor >= umbral - holgura else ROJO


def _valor_periodo_anterior(doc):
    """El valor del mismo indicador y ámbito en el periodo inmediatamente anterior.

    Se consulta con `get_all` a propósito: es el cálculo derivado del documento
    que se está guardando, no una lista que se le muestre a nadie. Si el usuario
    no puede ver la medición anterior, su semáforo sigue teniendo que ser
    correcto — lo contrario daría colores distintos según quién guarde.
    """
    if not doc.get("periodo_academico"):
        return None

    inicio_actual = frappe.db.get_value("Periodo Academico", doc.periodo_academico, "fecha_inicio")
    if not inicio_actual:
        return None

    filtros = {"indicador": doc.indicador, "name": ["!=", doc.name or ""]}
    # El ámbito tiene que ser el mismo: comparar el dato de un programa con el de
    # otro no dice nada sobre la evolución de ninguno de los dos.
    for campo in ("programa_sede", "unidad_organica"):
        filtros[campo] = doc.get(campo) or ["is", "not set"]

    candidatos = frappe.get_all(
        "Valor Indicador",
        filters=filtros,
        fields=["name", "valor_num", "periodo_academico"],
        limit=0,
    )
    anteriores = []
    for c in candidatos:
        if c.valor_num is None or not c.periodo_academico:
            continue
        inicio = frappe.db.get_value("Periodo Academico", c.periodo_academico, "fecha_inicio")
        if inicio and str(inicio) < str(inicio_actual):
            anteriores.append((str(inicio), flt(c.valor_num)))

    if not anteriores:
        return None
    anteriores.sort()
    return anteriores[-1][1]


def _por_evolucion(valor, anterior, sentido, margen_pct):
    """Verde si mejora; ámbar si se mantiene dentro del margen; rojo si empeora."""
    holgura = abs(flt(anterior) * flt(margen_pct) / 100.0) if margen_pct else 0.0
    diferencia = valor - anterior

    if sentido == MENOR_MEJOR:
        diferencia = -diferencia

    if diferencia > 0:
        return VERDE
    return AMBAR if abs(diferencia) <= holgura else ROJO


def calcular(doc):
    """Devuelve Verde / Ambar / Rojo, o None cuando no hay con qué juzgar."""
    if doc.get("valor_num") is None:
        return None

    ficha = _ficha(doc.get("indicador"))
    if not ficha:
        return None

    valor = flt(doc.valor_num)
    sentido = (ficha.get("sentido") or MAYOR_MEJOR).strip()
    margen = ficha.get("margen_error")

    if _modo(ficha) == MODO_EVOLUCION:
        anterior = _valor_periodo_anterior(doc)
        if anterior is None:
            return None
        return _por_evolucion(valor, anterior, sentido, margen)

    umbral = ficha.get("valor_referencial")
    if umbral is None:
        return None
    return _por_umbral(valor, flt(umbral), sentido, margen)
