"""Chequeos de acceso: ¿puede entrar la gente que tiene que entrar? (#58)

El 20-sep-2026 cuatro cuentas de la DPGC quedaron sin poder abrir el Desk al
asignarles un rol sin `desk_access`. Estuvieron horas sin poder trabajar y
**nada lo detectó**: el sitio respondía 200, las cuentas existían, estaban
habilitadas y tenían su rol. Nadie preguntaba lo único que importaba — si podían
entrar.

Cómo funciona de verdad, verificado en el source de Frappe 16:

- `User.set_system_user` (`user.py:414-415`) deriva el tipo de los roles al
  GUARDAR: `System User` si alguno tiene `desk_access`, `Website User` si no.
- `desk.py:26-27` lanza `PermissionError` a un `Website User` que abre el Desk.

De ahí salen dos fallos distintos, y por eso hay dos chequeos y no uno:

1. **Ya degradada**: `user_type` es `Website User` pero sus roles dicen que
   debería trabajar en el Desk. Es el incidente del 20-sep. No puede entrar HOY.
2. **A punto de degradarse**: `user_type` es `System User` pero ninguno de sus
   roles tiene `desk_access`. Hoy entra, porque el campo aún dice lo contrario;
   al próximo guardado de la cuenta, Frappe recalcula y la deja fuera. Es una
   bomba de relojería que solo se ve mirando la coherencia entre ambas cosas.
"""

import frappe

from sgc.setup.f3b_rbac import ROLES
from sgc.verificacion import AVISO, BLOQUEANTE, INFO, Hallazgo

# Cuentas que el framework gestiona y que no son de nadie: no son hallazgo.
CUENTAS_DE_SISTEMA = {"Administrator", "Guest"}


def _usuarios_reales():
    """Las cuentas habilitadas que representan a una persona.

    Se excluyen las de sistema y las de servicio (`svc-*`), que existen para que
    una máquina llame a la API y **no deben** entrar al Desk: señalarlas sería
    ruido, y un aviso con ruido deja de leerse.
    """
    return [
        u
        for u in frappe.get_all(
            "User",
            filters={"enabled": 1},
            fields=["name", "full_name", "user_type"],
        )
        if u.name not in CUENTAS_DE_SISTEMA and not u.name.startswith("svc-")
    ]


def _roles_de(usuario):
    return frappe.get_all(
        "Has Role", filters={"parent": usuario, "parenttype": "User"}, pluck="role"
    )


def _roles_con_desk(roles):
    if not roles:
        return []
    return frappe.get_all(
        "Role", filters={"name": ["in", roles], "desk_access": 1}, pluck="name"
    )


def cuentas_que_no_pueden_entrar():
    """Habilitadas, con roles de trabajo, y fuera del Desk. El incidente del 20-sep."""
    afectadas = []

    for u in _usuarios_reales():
        if u.user_type != "Website User":
            continue
        roles = _roles_de(u.name)
        # Sin roles es otro problema, y lo reporta otro chequeo.
        if not roles:
            continue
        # Un Website User con roles que el catálogo declara CON acceso al Desk es
        # una cuenta que debería trabajar y no puede. Si sus roles son todos de
        # portal (p.ej. «Lector Externo»), ser Website User es lo correcto.
        declarados_con_desk = [r for r, desk in ROLES if desk and r in roles]
        if declarados_con_desk:
            afectadas.append((u, roles, declarados_con_desk))

    if not afectadas:
        return []

    detalle = [
        f"{u.full_name or u.name} <{u.name}> — roles: {', '.join(roles)} "
        f"(el catálogo declara con acceso: {', '.join(declarados)})"
        for u, roles, declarados in afectadas
    ]

    return [
        Hallazgo(
            AVISO,
            "acceso-denegado",
            f"{len(afectadas)} cuenta(s) habilitada(s) no pueden abrir el Desk.",
            detalle,
            remedio=(
                "Sus roles deberían dar acceso. Reejecutar "
                "`sgc.setup.f3b_rbac.run` reconcilia el catálogo y Frappe recalcula "
                "el tipo de usuario; comprobar después que `user_type` sea System User."
            ),
        )
    ]


def cuentas_a_punto_de_perder_el_acceso():
    """System User cuyos roles ya no dan `desk_access`: caen al próximo guardado."""
    afectadas = []

    for u in _usuarios_reales():
        if u.user_type == "Website User":
            continue
        roles = _roles_de(u.name)
        if not roles:
            continue
        if not _roles_con_desk(roles):
            afectadas.append((u, roles))

    if not afectadas:
        return []

    detalle = [
        f"{u.full_name or u.name} <{u.name}> — roles: {', '.join(roles)}"
        for u, roles in afectadas
    ]

    return [
        Hallazgo(
            AVISO,
            "acceso-en-riesgo",
            f"{len(afectadas)} cuenta(s) entran hoy, pero ninguno de sus roles da acceso al Desk.",
            detalle,
            remedio=(
                "Frappe deriva el tipo de usuario de los roles al guardar la cuenta "
                "(`user.py:414-415`): al próximo guardado pasarán a Website User y "
                "dejarán de entrar. Darles un rol con `desk_access` antes de que ocurra."
            ),
        )
    ]


def roles_del_catalogo_divergentes():
    """Roles cuyo `desk_access` no coincide con lo declarado. La causa raíz (#57)."""
    divergentes = []

    for role_name, declarado in ROLES:
        actual = frappe.db.get_value("Role", role_name, "desk_access")
        if actual is None:
            divergentes.append(f"{role_name} — NO EXISTE (declarado desk_access={declarado})")
        elif int(actual) != int(declarado):
            divergentes.append(
                f"{role_name} — desk_access={int(actual)}, el catálogo declara {declarado}"
            )

    if not divergentes:
        return []

    return [
        Hallazgo(
            AVISO,
            "catalogo-divergente",
            f"{len(divergentes)} rol(es) del catálogo no coinciden con lo declarado.",
            divergentes,
            remedio=(
                "`sgc.setup.f3b_rbac.run` los reconcilia. Se comprueba aunque el "
                "despliegue lo corrija: esto detecta los cambios hechos a mano desde "
                "la interfaz, que es de donde vino el incidente del 20-sep-2026."
            ),
        )
    ]


def cuentas_sin_rol():
    """Existen, están habilitadas y no pueden hacer nada."""
    sin_rol = [u for u in _usuarios_reales() if not _roles_de(u.name)]

    if not sin_rol:
        return []

    return [
        Hallazgo(
            INFO,
            "cuenta-sin-rol",
            f"{len(sin_rol)} cuenta(s) habilitada(s) sin ningún rol asignado.",
            [f"{u.full_name or u.name} <{u.name}>" for u in sin_rol],
            remedio="O se les asigna un rol, o se deshabilitan: habilitadas y sin rol no sirven.",
        )
    ]


def nadie_puede_entrar():
    """El caso bloqueante: la instancia responde y no le sirve a nadie."""
    usuarios = _usuarios_reales()
    if not usuarios:
        # Una instancia recién creada, sin usuarios todavía, no está rota.
        return []

    if any(u.user_type != "Website User" for u in usuarios):
        return []

    return [
        Hallazgo(
            BLOQUEANTE,
            "instancia-sin-acceso",
            "Ninguna cuenta puede abrir el Desk. La instancia responde y es inservible.",
            [f"{len(usuarios)} cuenta(s) habilitada(s), todas Website User"],
            remedio=(
                "Comprobar el catálogo de roles con `sgc.setup.f3b_rbac.run` y que al "
                "menos un rol con `desk_access` esté asignado a alguien."
            ),
        )
    ]


CHEQUEOS = [
    nadie_puede_entrar,
    cuentas_que_no_pueden_entrar,
    cuentas_a_punto_de_perder_el_acceso,
    roles_del_catalogo_divergentes,
    cuentas_sin_rol,
]
