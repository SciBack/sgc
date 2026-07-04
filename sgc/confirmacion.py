"""Confirmación humana del nivel oficial NL/L/LP por estándar — cierre de la cadena F2.

El motor (`scoring.py`) solo PROPONE (`Valoracion Estandar.nivel_propuesto`); NUNCA
escribe el campo oficial `nivel` (Link→`Nivel Escala`, permlevel 1). Este módulo es la
ACCIÓN HUMANA que confirma ese `nivel` y, una vez confirmados los 10 estándares, PROMUEVE
la vigencia oficial (`Autoevaluacion.resultado_vigencia`).

Separación de responsabilidades (respetada literalmente):

  motor  ->  nivel_propuesto        (scoring.proponer_nivel_estandar)
  humano ->  nivel + confirmado=1   (confirmar_nivel / confirmar_todos_propuestos)
  humano ->  resultado_vigencia     (finalizar_vigencia, tras 10/10 confirmados)

Estas funciones ESCRIBEN el campo permlevel-1 `nivel` con `ignore_permissions=True`
DENTRO de la función: la función misma ES la acción autorizada. En producción el acceso
se restringe por ROL al método whitelisted (no por el permlevel de campo), reservando
además el "seam" para invocación vía MCP.

--- Mapeos ------------------------------------------------------------------

sigla ↔ Nivel Escala:
  El argumento `nivel_sigla` es la sigla NL/L/LP. Se resuelve al `name` del registro
  `Nivel Escala` cuya `sigla`==nivel_sigla (case-insensitive, trim). Ese `name` es lo
  que se guarda en el Link `Valoracion Estandar.nivel`. (`scoring._sigla_nivel` hace el
  camino inverso name→sigla al recalcular vigencia.)

propuesta (motor, SIN tilde) ↔ oficial (con tilde):
  "En proceso"          -> "En proceso"
  "Acreditado 3 anios"  -> "Acreditado 3 años"
  "Acreditado 6 anios"  -> "Acreditado 6 años"
  "Acreditado 8 anios"  -> "Acreditado 8 años"
  (Las opciones oficiales viven en `Autoevaluacion.resultado_vigencia`; las del motor,
  sin tilde, en `vigencia_propuesta`.)
"""
import frappe
from frappe import _

from sgc import scoring

NIVELES_VALIDOS = {"NL", "L", "LP"}
TOTAL_ESTANDARES = 10

# Propuesta del motor (sin tilde) -> opción oficial (con tilde) de resultado_vigencia.
_VIGENCIA_PROPUESTA_A_OFICIAL = {
    "En proceso": "En proceso",
    "Acreditado 3 anios": "Acreditado 3 años",
    "Acreditado 6 anios": "Acreditado 6 años",
    "Acreditado 8 anios": "Acreditado 8 años",
}


# ===========================================================================
# Helpers
# ===========================================================================

def _nivel_escala_de_sigla(nivel_sigla):
    """`name` del registro `Nivel Escala` cuya `sigla` == nivel_sigla (NL/L/LP)."""
    if not nivel_sigla:
        return None
    sigla = str(nivel_sigla).strip().upper()
    if sigla not in NIVELES_VALIDOS:
        return None
    # Nivel Escala es child table (istable); sus filas maestras son referenciables
    # como Link por `name`. Se localiza por su `sigla`.
    return frappe.db.get_value("Nivel Escala", {"sigla": sigla}, "name")


def _get_o_crea_valoracion_estandar(autoevaluacion, estandar):
    """Localiza (autoevaluacion+elemento_marco) o crea la `Valoracion Estandar`."""
    name = frappe.db.get_value(
        "Valoracion Estandar",
        {"autoevaluacion": autoevaluacion, "elemento_marco": estandar},
        "name",
    )
    if name:
        return frappe.get_doc("Valoracion Estandar", name)
    ve = frappe.new_doc("Valoracion Estandar")
    ve.autoevaluacion = autoevaluacion
    ve.elemento_marco = estandar
    return ve


# ===========================================================================
# Confirmación por estándar
# ===========================================================================

@frappe.whitelist()
def confirmar_nivel(autoevaluacion, estandar, nivel_sigla, comentario=None):
    """Confirma el `nivel` oficial (NL/L/LP) de un estándar en una autoevaluación.

    El humano puede confirmar el `nivel_propuesto` tal cual, o hacer un OVERRIDE
    justificado. Setea `nivel` (permlevel 1), `confirmado=1`, `aprobado_por`=usuario
    actual y `estado`="Aprobado". Idempotente: reconfirmar el mismo valor no rompe.

    LP no es mecánico: al confirmar LP se espera que `comentario` refiera la revisión
    de indicadores (±3%, 4 semestres). No se fuerza, pero se deja el campo.
    """
    if not autoevaluacion or not estandar:
        frappe.throw(_("Se requieren `autoevaluacion` y `estandar`."))

    sigla = str(nivel_sigla or "").strip().upper()
    if sigla not in NIVELES_VALIDOS:
        frappe.throw(_("`nivel_sigla` inválido: {0}. Use NL/L/LP.").format(nivel_sigla))

    nivel_name = _nivel_escala_de_sigla(sigla)
    if not nivel_name:
        frappe.throw(_("No existe un `Nivel Escala` con sigla {0}.").format(sigla))

    ve = _get_o_crea_valoracion_estandar(autoevaluacion, estandar)

    # ¿El humano difiere del propuesto por el motor? -> override; conservar traza.
    propuesto = (ve.nivel_propuesto or "").strip().upper()
    es_override = bool(propuesto) and propuesto != sigla

    ve.nivel = nivel_name
    ve.confirmado = 1
    ve.aprobado_por = frappe.session.user
    if ve.meta.has_field("estado"):
        ve.estado = "Aprobado"

    # Comentario/observación: obligatorio conceptualmente si hay override; se guarda
    # en `justificacion`. También se registra cuando el humano lo aporta para LP.
    if comentario:
        ve.justificacion = comentario
    elif es_override and not ve.justificacion:
        ve.justificacion = _(
            "Override manual: motor propuso {0}, el evaluador confirmó {1}."
        ).format(propuesto, sigla)

    ve.flags.ignore_version = True
    # La función ES la acción autorizada -> se salta el permlevel de campo aquí dentro.
    ve.save(ignore_permissions=True)

    return {
        "ok": True,
        "valoracion_estandar": ve.name,
        "nivel": nivel_name,
        "sigla": sigla,
        "override": es_override,
        "propuesto": propuesto or None,
    }


@frappe.whitelist()
def confirmar_todos_propuestos(autoevaluacion):
    """Confirma en bloque cada estándar con `nivel_propuesto` no vacío y sin confirmar.

    Confirma `nivel` = el propuesto por el motor. Idempotente: los ya confirmados se
    saltan. Útil para cerrar rápido y para el E2E. Devuelve cuántos confirmó.
    """
    if not autoevaluacion:
        frappe.throw(_("Se requiere `autoevaluacion`."))

    filas = frappe.get_all(
        "Valoracion Estandar",
        filters={"autoevaluacion": autoevaluacion},
        fields=["name", "elemento_marco", "nivel_propuesto", "confirmado"],
    )

    confirmados = 0
    for fila in filas:
        propuesto = (fila.get("nivel_propuesto") or "").strip().upper()
        if not propuesto or propuesto not in NIVELES_VALIDOS:
            continue
        if fila.get("confirmado"):
            continue
        confirmar_nivel(autoevaluacion, fila["elemento_marco"], propuesto)
        confirmados += 1

    return {"ok": True, "confirmados": confirmados}


# ===========================================================================
# Finalización: promueve la vigencia oficial
# ===========================================================================

@frappe.whitelist()
def finalizar_vigencia(autoevaluacion):
    """Exige 10/10 estándares confirmados; si están, promueve la vigencia oficial.

    - Cuenta las `Valoracion Estandar` de la autoevaluación con `confirmado=1` y `nivel`.
    - Si faltan, devuelve {ok: False, faltan: N} (no toca nada).
    - Si están los 10, llama `scoring.proponer_vigencia` (lee los `nivel` confirmados,
      aplica la Tabla 9) y MAPEA la propuesta (sin tilde) a la opción oficial (con tilde)
      del campo `Autoevaluacion.resultado_vigencia`.
    Idempotente. Devuelve {ok: True, vigencia: "<oficial>"}.
    """
    if not autoevaluacion:
        frappe.throw(_("Se requiere `autoevaluacion`."))

    confirmados = frappe.db.count(
        "Valoracion Estandar",
        {"autoevaluacion": autoevaluacion, "confirmado": 1, "nivel": ["is", "set"]},
    )

    if confirmados < TOTAL_ESTANDARES:
        return {
            "ok": False,
            "faltan": TOTAL_ESTANDARES - confirmados,
            "confirmados": confirmados,
        }

    # El motor recalcula la vigencia sobre los `nivel` ya confirmados (Tabla 9)
    # y persiste `vigencia_propuesta` (sin tilde).
    resultado = scoring.proponer_vigencia(autoevaluacion)
    propuesta = resultado.get("vigencia_propuesta")

    if not propuesta:
        # No debería ocurrir con 10/10 confirmados, pero se protege el contrato.
        return {
            "ok": False,
            "faltan": 0,
            "confirmados": confirmados,
            "error": _("El motor no pudo proponer vigencia pese a 10/10 confirmados."),
        }

    oficial = _VIGENCIA_PROPUESTA_A_OFICIAL.get(propuesta)
    if not oficial:
        frappe.throw(
            _("Vigencia propuesta desconocida (sin mapeo oficial): {0}").format(propuesta)
        )

    frappe.db.set_value(
        "Autoevaluacion", autoevaluacion, "resultado_vigencia", oficial
    )

    return {"ok": True, "vigencia": oficial, "vigencia_propuesta": propuesta}
