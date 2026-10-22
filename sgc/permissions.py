# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M07 — Visibilidad por programa y por sede (opt-in, seguro).

Mecanismo que acota lo que ve un usuario a SUS Programa Sede **solo si** se le
asignó una `User Permission`, de una de dos formas:

  - sobre `Programa Sede` (un programa concreto), o
  - sobre su **sede**: `Unidad Organica` de tipo Sede (Lima, Juliaca, Tarapoto).
    Equivale a todos los Programa Sede de esa sede, también los que se creen
    después. `asignar_sede` la crea aplicable SOLO a `Programa Sede`: así lo
    institucional (lo que no es de un programa) lo sigue viendo. Una User
    Permission de sede «para todos los DocTypes» (ver `otorgar_ambito`) acota
    además, de forma nativa, todo lo que enlace una unidad fuera de su subárbol:
    sirve donde las unidades cuelgan de su sede, no donde las sedes son hojas.

Quien NO tenga ninguna de las dos —o tenga un rol exento— ve TODO. Es *opt-in*:
sin User Permission sembrada, el mecanismo queda INACTIVO (todos ven todo).

Dos ejes (patrón Frappe):
  1. `permission_query_conditions` -> filtra los LISTADOS (SQL WHERE inyectado).
  2. `has_permission`               -> filtra el acceso a UN documento (get_doc).
Ambos registrados en hooks.py por DocType.

Regla de exención (decisión de Alberto, 22-oct-2026: «la sede manda»):
  EXENTOS (ven todo):  DPGC, System Manager, Administrator, y CUALQUIERA sin
                       User Permission de programa ni de sede.
  ACOTADOS:            cualquier otro usuario con esa User Permission, también
                       un "Analista de Calidad (DPGC)" o un "Auditor Interno":
                       asignarle una sede es decir a propósito que trabaja solo
                       en ella (p.ej. Planificación Tarapoto).

DocTypes acotados (derivación de programa NO AMBIGUA):
  - Autoevaluacion       -> campo directo `programa_sede`.
  - Hallazgo             -> campo directo `programa_sede`.
  - No Conformidad       -> campo directo `programa_sede`.
  - Valoracion Criterio  -> vía padre `autoevaluacion` -> Autoevaluacion.programa_sede.
  - Valoracion Estandar  -> vía padre `autoevaluacion` -> Autoevaluacion.programa_sede.
  - Plan Mejora          -> vía `autoevaluacion` -> Autoevaluacion.programa_sede.
  - Salida No Conforme, Valor Indicador, Alerta Indicador, Auditoria, Comite
                         -> campo directo `programa_sede`.

DocTypes deliberadamente NO acotados (ver notas al pie del archivo):
  - Accion Mejora  -> derivación AMBIGUA (plan_mejora / hallazgo / no_conformidad,
                      todos opcionales; múltiples padres posibles).
  - Evidencia / Evidencia Enlace / Trazabilidad -> relación N:M (una evidencia
                      puede sustentar varios programas); no hay programa único.

Semántica del NULL: un registro cuyo programa deriva a NULL (p.ej. una
Autoevaluacion institucional sin `programa_sede`, o un Hallazgo de proceso) NO se
oculta a nadie — no es atribuible a ningún programa, así que se comparte. Esto
mantiene el aislamiento entre programas sin ocultar lo transversal.
"""
import frappe

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
DOCTYPE_PROGRAMA = "Programa Sede"
# Las sedes son unidades orgánicas de tipo «Sede» (Programa Sede.sede las enlaza).
DOCTYPE_SEDE = "Unidad Organica"
TIPO_SEDE = "Sede"

# Roles que SIEMPRE ven todo (ignoran cualquier User Permission de programa o sede).
ROLES_EXENTOS = frozenset({
    "DPGC",
    "System Manager",
})

# DocTypes con el Programa Sede en un campo directo `programa_sede`.
DOCTYPES_CAMPO_DIRECTO = (
    "Autoevaluacion",
    "Hallazgo",
    "No Conformidad",
    "Salida No Conforme",
    "Valor Indicador",
    "Alerta Indicador",
    "Auditoria",
    "Comite",
)


# ---------------------------------------------------------------------------
# Helper central: ¿a qué Programa(s) Sede está acotado el usuario?
# ---------------------------------------------------------------------------
def es_exento(user=None):
    """True si `user` ve todo por rol (o es Administrator)."""
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    return bool(ROLES_EXENTOS.intersection(frappe.get_roles(user)))


def es_sede(unidad):
    """True si `unidad` es una Unidad Organica de tipo Sede."""
    return bool(unidad) and frappe.db.get_value(DOCTYPE_SEDE, unidad, "tipo") == TIPO_SEDE


def sedes_asignadas(user=None):
    """Sedes (Unidad Organica de tipo Sede) asignadas a `user` por User Permission."""
    user = user or frappe.session.user
    unidades = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": DOCTYPE_SEDE},
        pluck="for_value",
    )
    if not unidades:
        return []
    return frappe.get_all(
        DOCTYPE_SEDE, filters={"name": ["in", unidades], "tipo": TIPO_SEDE}, pluck="name"
    )


def programas_permitidos(user=None):
    """Lista de `Programa Sede` a los que el usuario está acotado, o `None` si NO
    está acotado (ve todo).

    Devuelve `None` (sin restricción) cuando:
      - el usuario es exento por rol (o Administrator), o
      - no tiene User Permission ni sobre Programa Sede ni sobre una sede (opt-in).

    Devuelve los names de Programa Sede cuando sí está acotado: los asignados uno
    a uno más todos los de sus sedes. Puede ser una lista vacía (una sede sin
    programas todavía): entonces solo ve lo que no es de ningún programa.

    `frappe.get_all` ignora permisos por diseño, así que consultar aquí las User
    Permission no recursa sobre estos mismos hooks.
    """
    user = user or frappe.session.user
    if es_exento(user):
        return None
    programas = set(frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": DOCTYPE_PROGRAMA},
        pluck="for_value",
    ))
    sedes = sedes_asignadas(user)
    if not programas and not sedes:
        return None  # opt-in: sin User Permission => sin restricción
    if sedes:
        programas.update(frappe.get_all(
            DOCTYPE_PROGRAMA, filters={"sede": ["in", sedes]}, pluck="name"
        ))
    return sorted(programas)


# ---------------------------------------------------------------------------
# Constructores de la condición SQL (permission_query_conditions)
# ---------------------------------------------------------------------------
def _in_list(programas):
    """'PS-A', 'PS-B'  (ya escapado) para un IN (...)."""
    return ", ".join(frappe.db.escape(p) for p in programas)


def _sin_programa_o_en(columna, programas):
    """`columna` vacía o dentro de `programas`. Con la lista vacía, solo vacía:
    un `in ()` es un error de sintaxis en SQL."""
    if not programas:
        return f"{columna} is null"
    return f"({columna} is null or {columna} in ({_in_list(programas)}))"


def _cond_directo(doctype, user, campo="programa_sede"):
    """Condición para DocTypes con el `Programa Sede` en un campo directo.

    Muestra el registro si su programa está en el conjunto permitido O si es NULL
    (no atribuible a ningún programa => compartido).
    """
    programas = programas_permitidos(user)
    if programas is None:
        return ""  # sin restricción
    return _sin_programa_o_en(f"`tab{doctype}`.`{campo}`", programas)


def _cond_via_autoevaluacion(doctype, user, campo="autoevaluacion",
                             padre_opcional=False):
    """Condición para DocTypes que derivan el programa por su padre Autoevaluacion.

    El registro es visible si su Autoevaluacion pertenece a un programa permitido
    (o a NINGún programa: AE institucional). Si `padre_opcional`, un registro sin
    Autoevaluacion (no atribuible a programa) también se muestra.
    """
    programas = programas_permitidos(user)
    if programas is None:
        return ""  # sin restricción
    tbl = f"`tab{doctype}`"
    sub = (
        "select name from `tabAutoevaluacion` "
        f"where {_sin_programa_o_en('`tabAutoevaluacion`.programa_sede', programas)}"
    )
    cond = f"{tbl}.`{campo}` in ({sub})"
    if padre_opcional:
        cond = f"({tbl}.`{campo}` is null or {cond})"
    return cond


# --- Funciones nombradas registradas en hooks.py (una por DocType) ---------
def pqc_autoevaluacion(user):
    return _cond_directo("Autoevaluacion", user)


def pqc_hallazgo(user):
    return _cond_directo("Hallazgo", user)


def pqc_no_conformidad(user):
    return _cond_directo("No Conformidad", user)


def pqc_salida_no_conforme(user):
    return _cond_directo("Salida No Conforme", user)


def pqc_valor_indicador(user):
    return _cond_directo("Valor Indicador", user)


def pqc_alerta_indicador(user):
    return _cond_directo("Alerta Indicador", user)


def pqc_auditoria(user):
    return _cond_directo("Auditoria", user)


def pqc_comite(user):
    return _cond_directo("Comite", user)


def pqc_valoracion_criterio(user):
    return _cond_via_autoevaluacion("Valoracion Criterio", user)


def pqc_valoracion_estandar(user):
    return _cond_via_autoevaluacion("Valoracion Estandar", user)


def pqc_plan_mejora(user):
    # `autoevaluacion` es opcional en Plan Mejora (puede nacer de un Hallazgo/NC
    # de proceso): un plan sin AE no es atribuible a un programa => visible.
    return _cond_via_autoevaluacion("Plan Mejora", user, padre_opcional=True)


# ---------------------------------------------------------------------------
# has_permission (acceso a UN documento — get_doc)
# ---------------------------------------------------------------------------
def _programa_del_doc(doc):
    """Programa Sede derivado del documento, o None si no es atribuible."""
    dt = doc.doctype
    if dt in DOCTYPES_CAMPO_DIRECTO:
        return doc.get("programa_sede")
    if dt in ("Valoracion Criterio", "Valoracion Estandar", "Plan Mejora"):
        ae = doc.get("autoevaluacion")
        if not ae:
            return None
        return frappe.db.get_value("Autoevaluacion", ae, "programa_sede")
    return None


def has_permission(doc, ptype=None, user=None):
    """Coherente con `permission_query_conditions`: un doc es visible si el usuario
    no está acotado, o si el programa del doc es NULL, o está en su conjunto.

    Devuelve True para no interferir con el resto de la evaluación de permisos de
    Frappe (los DocPerm por rol siguen aplicando por separado)."""
    programas = programas_permitidos(user or frappe.session.user)
    if programas is None:
        return True
    prog = _programa_del_doc(doc)
    if prog is None:
        return True  # registro no atribuible a un programa => compartido
    return prog in programas


# ===========================================================================
# NOTA — DocTypes NO acotados a propósito (derivación ambigua o N:M)
# ===========================================================================
# - "Accion Mejora": no tiene programa_sede ni autoevaluacion propios; el
#   programa habría que inferirlo por su plan_mejora, hallazgo o no_conformidad
#   —los tres opcionales y potencialmente en conflicto—. Derivación AMBIGUA =>
#   NO se acota. (Su plan_mejora padre sí queda acotado, que es el pivote real.)
# - "Evidencia" / "Evidencia Enlace" / "Trazabilidad": una misma evidencia puede
#   sustentar criterios/procesos de VARIOS programas (relación N:M vía
#   Trazabilidad). No existe un programa único => acotarlas ocultaría evidencia
#   legítimamente compartida. NO se acotan.
# Si en el futuro se requiere acotar Evidencia, hágase por política explícita
# (p.ej. un campo `programa_sede` de "dueño") y no por inferencia.


# ---------------------------------------------------------------------------
# Activación (la forma CORRECTA de asignar el programa a un usuario)
# ---------------------------------------------------------------------------
# DocTypes con Link DIRECTO a Programa Sede que SÍ queremos acotar. La User
# Permission se crea con apply_to_all_doctypes=0 + applicable_for = SOLO estos,
# para que el mecanismo NATIVO de Frappe no acote de rebote otros direct-linkers
# (Evidencia, Aplicacion Instrumento, Carga Evidencias), que deben quedar
# compartidos. Los derivados por padre (Valoracion*, Plan Mejora) ya los cubren
# las get_permission_query_conditions de arriba.
DOCTYPES_ACOTADOS_DIRECTOS = DOCTYPES_CAMPO_DIRECTO


@frappe.whitelist()
def otorgar_programa(user, programa_sede):
    """Acota a `user` a `programa_sede` — así se ACTIVA M07 para una persona.

    Crea (idempotente) una User Permission sobre Programa Sede por cada DocType
    de acotamiento directo, con apply_to_all_doctypes=0, para no restringir de
    rebote Evidencia/Comite/Auditoria. Un usuario puede tener varias (varios
    programas). Ejecutar p.ej.:
        bench --site <site> execute sgc.permissions.otorgar_programa \
            --kwargs '{"user":"persona@example.org","programa_sede":"PROG-SEDE"}'
    """
    frappe.only_for(("DPGC", "System Manager"))
    creadas = 0
    for dt in DOCTYPES_ACOTADOS_DIRECTOS:
        existe = frappe.db.exists(
            "User Permission",
            {"user": user, "allow": "Programa Sede", "for_value": programa_sede, "applicable_for": dt},
        )
        if existe:
            continue
        up = frappe.get_doc({
            "doctype": "User Permission",
            "user": user,
            "allow": "Programa Sede",
            "for_value": programa_sede,
            "apply_to_all_doctypes": 0,
            "applicable_for": dt,
        })
        up.flags.ignore_permissions = True
        up.insert(ignore_permissions=True)
        creadas += 1
    return {"user": user, "programa_sede": programa_sede, "user_permissions_creadas": creadas}


@frappe.whitelist()
def asignar_sede(user, sede):
    """Acota a `user` a los programas de `sede` (Lima, Juliaca, Tarapoto…).

    Crea (idempotente) UNA User Permission sobre la sede, aplicable solo a
    Programa Sede. Frappe filtra entonces por sí solo la lista y los desplegables
    de Programa Sede, y `programas_permitidos` deriva de ella todos los programas
    de la sede para el resto. Lo que no es de ningún programa lo sigue viendo.

    Desde el Desk es lo mismo que crear la User Permission a mano: Permitir
    «Unidad Organica», Valor la sede, sin «Aplicar a todos los tipos de
    documento» y Aplicable a «Programa Sede».

        bench --site <site> execute sgc.permissions.asignar_sede \\
            --kwargs '{"user":"persona@example.org","sede":"SEDE-X"}'
    """
    frappe.only_for(("DPGC", "System Manager"))
    if not es_sede(sede):
        frappe.throw(f"«{sede}» no es una unidad orgánica de tipo {TIPO_SEDE}.")
    filtros = {"user": user, "allow": DOCTYPE_SEDE, "for_value": sede, "applicable_for": DOCTYPE_PROGRAMA}
    if frappe.db.exists("User Permission", filtros):
        return {"user": user, "sede": sede, "creada": False}
    up = frappe.get_doc({"doctype": "User Permission", **filtros, "apply_to_all_doctypes": 0})
    up.flags.ignore_permissions = True
    up.insert(ignore_permissions=True)
    return {"user": user, "sede": sede, "creada": True}


# Dimensiones de ámbito que el framework resuelve por sí solo. Son DocTypes
# árbol: una User Permission sobre un nodo alcanza a sus descendientes sin
# configuración extra, así que aquí SÍ conviene apply_to_all_doctypes=1 (a
# diferencia de Programa Sede, acotado por DocType para no restringir de rebote
# las relaciones N:M como Evidencia).
DIMENSIONES_ARBOL = ("Unidad Organica", "Proceso")


@frappe.whitelist()
def otorgar_ambito(user, unidad_organica=None, programa_sede=None, proceso=None):
    """Siembra el ámbito de una persona en las dimensiones que se le indiquen.

    Es el procedimiento de activación: mientras nadie llame a esto, el usuario
    ve todo (opt-in). Idempotente: repetirlo no duplica User Permission.

    Las dimensiones se INTERSECTAN. Dar sede y proceso a la vez deja ver solo lo
    que cumple ambas, que es cómo el motor de permisos une condiciones de
    doctypes distintos. Dar dos valores de la misma dimensión los suma.

        bench --site <site> execute sgc.permissions.otorgar_ambito \\
            --kwargs '{"user":"x@dominio","unidad_organica":"SEDE-X","proceso":"P-01"}'
    """
    frappe.only_for(("DPGC", "System Manager"))
    resultado = {"user": user, "creadas": 0, "ya_existian": 0, "dimensiones": []}

    if programa_sede:
        # Delegado: Programa Sede tiene su propia semántica por DocType.
        r = otorgar_programa(user, programa_sede)
        resultado["creadas"] += r["user_permissions_creadas"]
        resultado["dimensiones"].append(f"Programa Sede={programa_sede}")

    for allow, valor in (("Unidad Organica", unidad_organica), ("Proceso", proceso)):
        if not valor:
            continue
        if not frappe.db.exists(allow, valor):
            frappe.throw(f"No existe {allow} «{valor}»")
        if frappe.db.exists("User Permission",
                            {"user": user, "allow": allow, "for_value": valor}):
            resultado["ya_existian"] += 1
            continue
        up = frappe.get_doc({
            "doctype": "User Permission", "user": user,
            "allow": allow, "for_value": valor,
            "apply_to_all_doctypes": 1,
        })
        up.flags.ignore_permissions = True
        up.insert(ignore_permissions=True)
        resultado["creadas"] += 1
        resultado["dimensiones"].append(f"{allow}={valor}")

    return resultado


@frappe.whitelist()
def ambito_de(user):
    """Qué ámbito tiene sembrado una persona, por dimensión.

    Sirve para verificar una activación sin leer la tabla a mano: si devuelve
    todo vacío, esa persona ve TODO (el mecanismo está inactivo para ella).
    """
    filas = frappe.get_all(
        "User Permission",
        filters={"user": user},
        fields=["allow", "for_value", "applicable_for"],
    )
    por_dimension = {}
    for f in filas:
        por_dimension.setdefault(f["allow"], set()).add(f["for_value"])
    return {
        "user": user,
        "acotado": bool(por_dimension),
        "exento_por_rol": es_exento(user),
        "ambito": {k: sorted(v) for k, v in por_dimension.items()},
    }
