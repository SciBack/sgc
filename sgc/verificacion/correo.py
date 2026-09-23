"""Chequeos del correo: ¿los avisos llegan a alguien? ¿salen de verdad? (#41)

Un rol destinatario sin usuarios con correo es un aviso que no llegará nunca, y
el sistema no falla: todos creen que funciona. Eso es AVISO. Que el correo esté
en ensayo o con lista blanca es INFO: puede ser justo lo que se quiere, pero
quien lee el informe tiene que saberlo.
"""

from sgc import correo
from sgc.verificacion import AVISO, INFO, Hallazgo


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


CHEQUEOS = [roles_destinatarios_vacios, modo_del_correo]
