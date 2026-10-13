"""Chequeos del correo: ¿hay por dónde salir? ¿los avisos llegan a alguien? (#41, #50)

Sin cuenta saliente, o con el correo silenciado, ningún aviso sale: AVISO.

Un rol destinatario sin usuarios con correo es un aviso que no llegará nunca, y
el sistema no falla: todos creen que funciona. Eso es AVISO. Que el correo esté
en ensayo o con lista blanca es INFO: puede ser justo lo que se quiere, pero
quien lee el informe tiene que saberlo.
"""

import frappe

from sgc import correo
from sgc.verificacion import AVISO, INFO, Hallazgo


def cuenta_saliente():
    """¿Hay por dónde salir? Sin cuenta saliente por defecto, nada sale, aunque todo lo demás esté bien.

    Se mira lo mismo que mira Frappe al enviar (`EmailAccount.find_default_outgoing`):
    una cuenta con envío y «por defecto», o el servidor declarado en site_config.
    Sin su último recurso, la cuenta ficticia que inventa con `mute_emails`: esa
    no envía a nadie. `mute_emails` se lee de site_config y no de `frappe.flags`,
    que los tests encienden y no dice nada de la instancia.
    """
    hallazgos = []
    if frappe.conf.get("mute_emails"):
        hallazgos.append(
            Hallazgo(
                AVISO,
                "correo-silenciado",
                "El correo está silenciado en site_config (`mute_emails`): no sale ningún aviso.",
                remedio="Quitar `mute_emails` de site_config.json si esta instancia debe avisar a la gente.",
            )
        )
    if not (frappe.db.get_value("Email Account", {"enable_outgoing": 1, "default_outgoing": 1})
            or frappe.conf.get("mail_server")):
        hallazgos.append(
            Hallazgo(
                AVISO,
                "correo-sin-cuenta-saliente",
                "No hay cuenta de correo saliente por defecto: las notificaciones no llegan a nadie.",
                remedio="Crear una Email Account con «Habilitar saliente» y «Saliente por defecto» marcados.",
            )
        )
    return hallazgos


def roles_destinatarios_vacios():
    vacios = correo.roles_sin_destinatarios()
    if not vacios:
        return []
    return [
        Hallazgo(
            AVISO,
            "correo-rol-sin-destinatarios",
            f"{len(vacios)} destinatario(s) por rol de reglas de correo no alcanzan a nadie.",
            detalle=[f"«{regla}» → rol {rol}: ningún usuario habilitado con correo" for regla, rol in vacios],
            remedio="Asignar el rol a quien deba recibir el aviso, o quitar el rol de la regla.",
        )
    ]


def modo_del_correo():
    reglas = correo.comprobar_destinatarios()
    if not reglas:
        return []
    if correo.modo() != correo.REAL:
        return [
            Hallazgo(
                INFO,
                "correo-en-ensayo",
                f"El correo está en modo ensayo: {len(reglas)} regla(s) activas no envían nada.",
                remedio="Se enciende en Configuracion Correo. Lo que se habría enviado está en Registro Correo.",
            )
        ]
    blanca = correo.lista_blanca()
    if blanca:
        return [
            Hallazgo(
                INFO,
                "correo-lista-blanca",
                f"El correo es real, pero solo para {len(blanca)} dirección(es) de la lista blanca.",
                detalle=blanca,
                remedio="Vaciar la lista blanca en Configuracion Correo cuando el estreno esté comprobado.",
            )
        ]
    return []


CHEQUEOS = [cuenta_saliente, roles_destinatarios_vacios, modo_del_correo]
