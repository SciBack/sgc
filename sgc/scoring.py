"""Motor de scoring de la autoevaluación — F2-CONTRATO.md §2 (Sección IX del Modelo CONEAU).

Reglas literales:

  Por estándar (proponer_nivel_estandar):
    criterios = hijos assessable (depth=3) del estándar en el marco
    vals      = Valoracion Criterio (de esta autoevaluación) de cada criterio
    algún criterio sin valorar        -> None (incompleto)
    algún "No cumple"                 -> "NL"
    algún "Cumple con debilidad"      -> "L"
    todos "Cumple"                    -> "LP"   (PROPUESTO; el humano confirma revisando
                                                 evolución de indicadores ±3%, 4 semestres)

  Vigencia (proponer_vigencia), sobre los `nivel` CONFIRMADOS de los 10 estándares (Tabla 9):
    no están los 10 confirmados       -> None (incompleto)
    algún "NL"                        -> "En proceso"
    todos "LP"                        -> "Acreditado 6 anios"   (8 años = Tabla 10, F6)
    resto (todos L, o combo L/LP)     -> "Acreditado 3 anios"

El sistema PROPONE (`nivel_propuesto`); el humano CONFIRMA (`nivel`, permlevel 1).
El motor NUNCA escribe `nivel`. LP no es mecánico.

"Estándar padre del criterio": el criterio es depth 3; su padre directo
(`parent_elemento_marco`) es el estándar depth 2. Ver `_estandar_padre_de_criterio`.
"""
import frappe

# --- Literales del campo `Valoracion Criterio.cumple` -----------------------
# El contrato §1 usa "Cumple con debilidad"; el DocType F1 real trae
# "Cumple parcial". El motor tolera ambos como el mismo juicio ("con debilidad").
CUMPLE_OK = "Cumple"
NO_CUMPLE = {"No cumple"}
CON_DEBILIDAD = {"Cumple con debilidad", "Cumple parcial"}
# "No aplica" / vacío se tratan como SIN valorar (no fijan nivel).

# --- Siglas de nivel --------------------------------------------------------
NIVELES_VALIDOS = {"NL", "L", "LP"}


def _sin_valorar(cumple):
    """True si el criterio NO tiene un juicio de cumplimiento real.

    Un criterio está valorado solo cuando su `cumple` es un juicio de
    cumplimiento: "Cumple", "Cumple parcial" o "No cumple". "No aplica" y el
    vacío/None NO valoran: el criterio aún no aporta ni a la propuesta de nivel
    del estándar ni al avance.

    Es la ÚNICA definición de "sin valorar" del motor: la comparten
    `proponer_nivel_estandar` (para dejar el estándar incompleto) y
    `_calcular_avance_pct` (para no contarlo en el numerador). Antes cada una
    tenía su propia regla y se contradecían: el avance contaba "No aplica" como
    valorado y llegaba a 100 % mientras el nivel dejaba ese mismo estándar como
    "incompleto" — justo el bug de "el porcentaje miente".
    """
    return cumple in (None, "", "No aplica")


# ===========================================================================
# Helpers de árbol
# ===========================================================================

def _sigla_nivel(nivel_name):
    """Convierte el `nivel` oficial (Link a Nivel Escala, o ya una sigla) a NL/L/LP.

    `Valoracion Estandar.nivel` es un Link a `Nivel Escala`; su valor es el `name`
    del registro. Se resuelve a su `sigla`. Si ya viene como sigla, se devuelve tal cual.
    """
    if not nivel_name:
        return None
    if nivel_name in NIVELES_VALIDOS:
        return nivel_name
    sigla = frappe.db.get_value("Nivel Escala", nivel_name, "sigla")
    if sigla:
        sigla = sigla.strip()
        if sigla in NIVELES_VALIDOS:
            return sigla
    # Fallback: tomar el prefijo del código/nombre (p.ej. "LP — ..." -> "LP").
    token = str(nivel_name).split()[0].strip().upper()
    return token if token in NIVELES_VALIDOS else None


def _estandar_padre_de_criterio(criterio_name):
    """Estándar (depth 2) padre de un criterio (depth 3): su `parent_elemento_marco`."""
    return frappe.db.get_value("Elemento Marco", criterio_name, "parent_elemento_marco")


def _marco_de_autoevaluacion(autoevaluacion):
    return frappe.db.get_value("Autoevaluacion", autoevaluacion, "marco_normativo")


def _criterios_de_estandar(estandar_name):
    """Criterios assessable (depth 3) del estándar: hijos directos valorables."""
    hijos = frappe.get_all(
        "Elemento Marco",
        filters={"parent_elemento_marco": estandar_name},
        fields=["name", "es_valorable", "tipo"],
    )
    # Preferir los marcados es_valorable; si el marco no lo denormalizó, caer a tipo=Criterio.
    valorables = [h.name for h in hijos if h.es_valorable]
    if valorables:
        return valorables
    return [h.name for h in hijos if (h.tipo or "") == "Criterio"]


def _criterios_valorables_del_marco(marco):
    """Criterios VALORABLES del marco: Elemento Marco tipo="Criterio" con es_valorable=1.

    Fuente ÚNICA de verdad del denominador del avance. EXCLUYE los estándares:
    el marco CONEAU marca `es_valorable=1` tanto en los 10 estándares (depth 2)
    como en los 53 criterios (depth 3), pero un estándar NO se valora con una
    Valoracion Criterio sino con un NIVEL. Contar los estándares como si fueran
    criterios (lo que hace `count(es_valorable=1)` = 63 en vez de 53) es lo que
    descuadraba el avance con el conteo real de criterios.

    Si el marco no denormalizó `es_valorable` en ningún criterio, cae a todos los
    `tipo="Criterio"` del marco.
    """
    if not marco:
        return []
    crits = frappe.get_all(
        "Elemento Marco",
        filters={"marco_normativo": marco, "tipo": "Criterio", "es_valorable": 1},
        pluck="name",
    )
    if crits:
        return crits
    return frappe.get_all(
        "Elemento Marco",
        filters={"marco_normativo": marco, "tipo": "Criterio"},
        pluck="name",
    )


def _estandares_de_autoevaluacion(autoevaluacion):
    """Los 10 estándares (depth 2) del marco de la autoevaluación."""
    marco = _marco_de_autoevaluacion(autoevaluacion)
    if not marco:
        return []
    ests = frappe.get_all(
        "Elemento Marco",
        filters={"marco_normativo": marco, "tipo": "Estandar"},
        fields=["name"],
        order_by="orden asc, codigo asc",
    )
    return [e.name for e in ests]


def _valoracion_criterio(autoevaluacion, criterio_name):
    """El juicio `cumple` de un criterio en una autoevaluación (o None si no valorado)."""
    return frappe.db.get_value(
        "Valoracion Criterio",
        {"autoevaluacion": autoevaluacion, "criterio": criterio_name},
        "cumple",
    )


# ===========================================================================
# Regla por estándar
# ===========================================================================

def proponer_nivel_estandar(autoevaluacion, estandar_name):
    """Calcula y hace upsert de `Valoracion Estandar.nivel_propuesto` (NL/L/LP o vacío).

    NUNCA toca `nivel` (oficial, permlevel 1). Devuelve la sigla propuesta (o None).
    """
    if not autoevaluacion or not estandar_name:
        return None

    criterios = _criterios_de_estandar(estandar_name)
    if not criterios:
        propuesto = None
    else:
        juicios = [_valoracion_criterio(autoevaluacion, c) for c in criterios]

        if any(_sin_valorar(v) for v in juicios):
            propuesto = None                                  # incompleto
        elif any(v in NO_CUMPLE for v in juicios):
            propuesto = "NL"
        elif any(v in CON_DEBILIDAD for v in juicios):
            propuesto = "L"
        elif all(v == CUMPLE_OK for v in juicios):
            propuesto = "LP"                                  # PROPUESTO; lo confirma el humano
        else:
            propuesto = None

    _upsert_valoracion_estandar(autoevaluacion, estandar_name, propuesto)
    return propuesto


def _upsert_valoracion_estandar(autoevaluacion, estandar_name, nivel_propuesto):
    """Crea o actualiza la Valoracion Estandar (autoevaluacion + elemento_marco).

    Solo setea `nivel_propuesto` (+ marca `calculado_auto`). No toca `nivel`.

    El DocType no tiene índice único sobre (autoevaluacion, elemento_marco), así
    que dos recomputos concurrentes podrían haber creado filas duplicadas del
    mismo par. Se auto-sana: se conserva la más antigua (donde vive el `nivel`
    confirmado por el humano) y se borran las extras, para que el informe no
    tome una arbitraria ni la vigencia cuente de más.
    """
    nombres = frappe.get_all(
        "Valoracion Estandar",
        filters={"autoevaluacion": autoevaluacion, "elemento_marco": estandar_name},
        pluck="name",
        order_by="creation asc",
    )
    if nombres:
        ve = frappe.get_doc("Valoracion Estandar", nombres[0])
        for extra in nombres[1:]:
            frappe.delete_doc(
                "Valoracion Estandar", extra, force=1, ignore_permissions=True
            )
    else:
        ve = frappe.new_doc("Valoracion Estandar")
        ve.autoevaluacion = autoevaluacion
        ve.elemento_marco = estandar_name

    ve.nivel_propuesto = nivel_propuesto or ""
    if ve.meta.has_field("calculado_auto"):
        ve.calculado_auto = 1
    ve.flags.ignore_permissions = True
    # ignore_version evita ruido de versión en recomputos masivos.
    ve.flags.ignore_version = True
    ve.save(ignore_permissions=True)
    return ve.name


# ===========================================================================
# Vigencia + avance (a nivel de autoevaluación)
# ===========================================================================

def proponer_vigencia(autoevaluacion):
    """Propone `vigencia_propuesta` (Tabla 9) y calcula `avance_pct`.

    Vigencia se basa en los `nivel` CONFIRMADOS de los 10 estándares; avance en el
    conteo de criterios valorados sobre el total de criterios del marco.
    """
    estandares = _estandares_de_autoevaluacion(autoevaluacion)

    # --- Vigencia (sobre niveles oficiales confirmados) ---
    niveles = []
    confirmados = 0
    for est in estandares:
        row = frappe.db.get_value(
            "Valoracion Estandar",
            {"autoevaluacion": autoevaluacion, "elemento_marco": est},
            ["nivel", "confirmado"],
            as_dict=True,
        )
        if row and row.get("confirmado") and row.get("nivel"):
            sigla = _sigla_nivel(row["nivel"])
            if sigla:
                niveles.append(sigla)
                confirmados += 1

    total_estandares = len(estandares)
    if total_estandares == 0 or confirmados < total_estandares:
        vigencia = None                                       # incompleto
    elif any(n == "NL" for n in niveles):
        vigencia = "En proceso"
    elif all(n == "LP" for n in niveles):
        vigencia = "Acreditado 6 anios"                       # 8 años = Tabla 10 (F6)
    else:
        vigencia = "Acreditado 3 anios"                       # todos L, o combo L/LP

    # --- Avance (criterios valorados / total criterios valorables del marco) ---
    avance = _calcular_avance_pct(autoevaluacion)

    frappe.db.set_value(
        "Autoevaluacion", autoevaluacion,
        {"vigencia_propuesta": vigencia or "", "avance_pct": avance},
        update_modified=False,
    )
    return {"vigencia_propuesta": vigencia, "avance_pct": avance}


def _calcular_avance_pct(autoevaluacion, estandares=None):
    """% de criterios del marco con un juicio de cumplimiento real.

    Definición explícita del avance (para que NO mienta):

      avance = criterios con juicio real / criterios VALORABLES del marco × 100

    - Denominador: `_criterios_valorables_del_marco` = solo los criterios
      (tipo="Criterio", es_valorable=1). Se EXCLUYEN los estándares, que también
      llevan es_valorable=1 en el marco CONEAU pero se valoran con un NIVEL, no
      con Valoracion Criterio. (Antes el denominador se armaba recorriendo los
      estándares y sumando sus criterios hijos; ahora se lee directo del marco,
      robusto ante criterios que no cuelguen de un estándar.)
    - Numerador: criterios NO `_sin_valorar`, i.e. con juicio de cumplimiento
      real (Cumple / Cumple parcial / No cumple). "No aplica" y vacío NO cuentan
      —igual que para el nivel—, así una autoevaluación con criterios en
      "No aplica" o sin tocar nunca llega a 100 %.

    `estandares` se mantiene por compatibilidad de firma pero ya no se usa: el
    denominador es del marco completo, no de los estándares recorridos.
    """
    marco = _marco_de_autoevaluacion(autoevaluacion)
    criterios = _criterios_valorables_del_marco(marco)
    total = len(criterios)
    if total == 0:
        return 0.0

    valorados = 0
    for c in criterios:
        cumple = _valoracion_criterio(autoevaluacion, c)
        if not _sin_valorar(cumple):
            valorados += 1

    return round(valorados * 100.0 / total, 2)


# ===========================================================================
# Recalculo completo
# ===========================================================================

def recalcular_autoevaluacion(autoevaluacion):
    """Recorre los 10 estándares (proponer_nivel_estandar) + vigencia + avance."""
    estandares = _estandares_de_autoevaluacion(autoevaluacion)
    propuestos = {}
    for est in estandares:
        propuestos[est] = proponer_nivel_estandar(autoevaluacion, est)

    resultado = proponer_vigencia(autoevaluacion)
    # Sin commit explícito: rompía el aislamiento transaccional de los tests
    # (filtraba registros entre casos) y en producción Frappe ya hace commit al
    # cerrar la request. Un contexto batch que lo necesite debe commitear él mismo.

    return {
        "estandares": propuestos,
        "vigencia_propuesta": resultado["vigencia_propuesta"],
        "avance_pct": resultado["avance_pct"],
    }
