# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M07 — Visibilidad por programa (opt-in, seguro).

Mecanismo que acota lo que ve un usuario a SU Programa Sede **solo si** se le
asignó una `User Permission` sobre `Programa Sede`. Quien NO tenga esa User
Permission —o tenga un rol exento— ve TODO. Es *opt-in*: mientras el orquestador
no siembre ninguna User Permission, el mecanismo queda INACTIVO (todos ven todo).

Dos ejes (patrón Frappe):
  1. `permission_query_conditions` -> filtra los LISTADOS (SQL WHERE inyectado).
  2. `has_permission`               -> filtra el acceso a UN documento (get_doc).
Ambos registrados en hooks.py por DocType.

Regla de exención (decisión de negocio, defaults delegados por Alberto):
  EXENTOS (ven todo):  DPGC, "Analista de Calidad (DPGC)", "Auditor Interno",
                       System Manager, Administrator, y CUALQUIERA sin User
                       Permission de Programa Sede.
  ACOTADOS:            "Responsable de Calidad de Programa" y
                       "Miembro de Comité de Calidad" (cuando tienen la User
                       Permission). En realidad se acota a *cualquier* usuario
                       con la User Permission que no sea exento — el rol acotado
                       es solo quien la recibe en el onboarding.

DocTypes acotados (derivación de programa NO AMBIGUA):
  - Autoevaluacion       -> campo directo `programa_sede`.
  - Hallazgo             -> campo directo `programa_sede`.
  - No Conformidad       -> campo directo `programa_sede`.
  - Valoracion Criterio  -> vía padre `autoevaluacion` -> Autoevaluacion.programa_sede.
  - Valoracion Estandar  -> vía padre `autoevaluacion` -> Autoevaluacion.programa_sede.
  - Plan Mejora          -> vía `autoevaluacion` -> Autoevaluacion.programa_sede.

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

# Roles que SIEMPRE ven todo (ignoran cualquier User Permission de Programa Sede).
ROLES_EXENTOS = frozenset({
    "DPGC",
    "Analista de Calidad (DPGC)",
    "Auditor Interno",
    "System Manager",
})


# ---------------------------------------------------------------------------
# Helper central: ¿a qué Programa(s) Sede está acotado el usuario?
# ---------------------------------------------------------------------------
def es_exento(user=None):
    """True si `user` ve todo por rol (o es Administrator)."""
    user = user or frappe.session.user
    if user == "Administrator":
        return True
    return bool(ROLES_EXENTOS.intersection(frappe.get_roles(user)))


def programas_permitidos(user=None):
    """Lista de `Programa Sede` a los que el usuario está acotado, o `None` si NO
    está acotado (ve todo).

    Devuelve `None` (sin restricción) cuando:
      - el usuario es exento por rol (o Administrator), o
      - no tiene NINGUNA User Permission sobre Programa Sede (opt-in).

    Devuelve una lista de names de Programa Sede cuando sí está acotado.

    `frappe.get_all` ignora permisos por diseño, así que consultar aquí las User
    Permission no recursa sobre estos mismos hooks.
    """
    user = user or frappe.session.user
    if es_exento(user):
        return None
    programas = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": DOCTYPE_PROGRAMA},
        pluck="for_value",
    )
    if not programas:
        return None  # opt-in: sin User Permission => sin restricción
    return programas


# ---------------------------------------------------------------------------
# Constructores de la condición SQL (permission_query_conditions)
# ---------------------------------------------------------------------------
def _in_list(programas):
    """'PS-A', 'PS-B'  (ya escapado) para un IN (...)."""
    return ", ".join(frappe.db.escape(p) for p in programas)


def _cond_directo(doctype, user, campo="programa_sede"):
    """Condición para DocTypes con el `Programa Sede` en un campo directo.

    Muestra el registro si su programa está en el conjunto permitido O si es NULL
    (no atribuible a ningún programa => compartido).
    """
    programas = programas_permitidos(user)
    if programas is None:
        return ""  # sin restricción
    tbl = f"`tab{doctype}`"
    return f"({tbl}.`{campo}` is null or {tbl}.`{campo}` in ({_in_list(programas)}))"


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
        f"where `tabAutoevaluacion`.programa_sede is null "
        f"or `tabAutoevaluacion`.programa_sede in ({_in_list(programas)})"
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
    if dt in ("Autoevaluacion", "Hallazgo", "No Conformidad"):
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
# (Evidencia, Comite, Auditoria, Aplicacion Instrumento, Valor Indicador), que
# deben quedar compartidos. Los derivados por padre (Valoracion*, Plan Mejora)
# ya los cubren las get_permission_query_conditions de arriba.
DOCTYPES_ACOTADOS_DIRECTOS = ("Autoevaluacion", "Hallazgo", "No Conformidad")


@frappe.whitelist()
def otorgar_programa(user, programa_sede):
    """Acota a `user` a `programa_sede` — así se ACTIVA M07 para una persona.

    Crea (idempotente) una User Permission sobre Programa Sede por cada DocType
    de acotamiento directo, con apply_to_all_doctypes=0, para no restringir de
    rebote Evidencia/Comite/Auditoria. Un usuario puede tener varias (varios
    programas). Ejecutar p.ej.:
        bench --site <site> execute sgc.permissions.otorgar_programa \
            --kwargs '{"user":"x@upeu.edu.pe","programa_sede":"ENF-LIMA"}'
    """
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
