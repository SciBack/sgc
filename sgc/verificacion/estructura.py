"""Chequeos de la estructura institucional: ¿hay sobre qué trabajar? (#50)

Lo que el despliegue NO crea porque es de cada institución: su árbol de unidades
y su periodo académico. Sin ellos el sistema arranca, la gente entra y las
pantallas se ven, pero no se puede asignar un proceso a nadie ni medir un
indicador. Por eso los dos primeros son BLOQUEANTE: una instancia recién
instalada que aún no se dio de alta tiene que decirlo, no parecer lista.
"""

import frappe
from frappe.utils import getdate, today

from sgc.verificacion import AVISO, BLOQUEANTE, INFO, Hallazgo

# Cuántos nombres se listan en un hallazgo antes de resumir el resto: lo
# bastante para actuar sin abrir la base, no tanto como para que nadie lo lea.
MAX_DETALLE = 15


def _recortar(nombres):
    if len(nombres) <= MAX_DETALLE:
        return list(nombres)
    return [*nombres[:MAX_DETALLE], f"… y {len(nombres) - MAX_DETALLE} más"]


def estructura_organizativa():
    unidades = frappe.db.count("Unidad Organica")
    if not unidades:
        return [
            Hallazgo(
                BLOQUEANTE,
                "sin-estructura",
                "No hay ninguna unidad orgánica: los procesos no se pueden asignar a nadie.",
                remedio="Cargar el árbol de unidades de la institución (Configuración → Unidades orgánicas).",
            )
        ]

    raices = frappe.get_all(
        "Unidad Organica",
        filters={"parent_unidad_organica": ["is", "not set"]},
        pluck="name",
        order_by="name asc",
    )
    if len(raices) > 1:
        return [
            Hallazgo(
                INFO,
                "estructura-varias-raices",
                f"El árbol de unidades tiene {len(raices)} raíces en vez de una.",
                detalle=_recortar(raices),
                remedio="Colgar cada unidad de su superior, para que los ámbitos por unidad abarquen lo que deben.",
            )
        ]
    return []


def periodo_vigente():
    abiertos = frappe.get_all(
        "Periodo Academico",
        filters={"estado": "abierto"},
        fields=["name", "fecha_inicio", "fecha_fin"],
        order_by="name asc",
    )
    if not abiertos:
        return [
            Hallazgo(
                BLOQUEANTE,
                "sin-periodo-vigente",
                "No hay ningún periodo académico abierto: los indicadores no se pueden medir.",
                remedio="Crear el periodo en curso con estado «abierto» (Configuración → Periodos académicos).",
            )
        ]

    hoy = getdate(today())
    vencidos = [p.name for p in abiertos if p.fecha_fin and getdate(p.fecha_fin) < hoy]
    sin_fechas = [p.name for p in abiertos if not (p.fecha_inicio and p.fecha_fin)]

    hallazgos = []
    if vencidos:
        hallazgos.append(
            Hallazgo(
                AVISO,
                "periodo-vencido-abierto",
                f"{len(vencidos)} periodo(s) siguen abiertos con la fecha de fin ya pasada.",
                detalle=vencidos,
                remedio="Cerrar el periodo terminado y abrir el siguiente: lo que se mida irá al periodo equivocado.",
            )
        )
    if sin_fechas:
        hallazgos.append(
            Hallazgo(
                AVISO,
                "periodo-sin-fechas",
                f"{len(sin_fechas)} periodo(s) abiertos sin fechas: no se puede comprobar que sigan vigentes.",
                detalle=sin_fechas,
                remedio="Declarar la fecha de inicio y de fin del periodo.",
            )
        )
    return hallazgos


def procesos_sin_responsable():
    sin = frappe.get_all(
        "Proceso",
        filters={"estado": "Vigente", "responsable": ["is", "not set"]},
        pluck="name",
        order_by="name asc",
    )
    if not sin:
        return []
    total = frappe.db.count("Proceso", {"estado": "Vigente"})
    return [
        Hallazgo(
            AVISO,
            "procesos-sin-responsable",
            f"{len(sin)} de {total} proceso(s) vigentes no tienen responsable: sus avisos no llegan a nadie.",
            detalle=_recortar(sin),
            remedio="Asignar el responsable en cada Proceso. La revisión de sus documentos recae mientras en quien los elaboró.",
        )
    ]


CHEQUEOS = [estructura_organizativa, periodo_vigente, procesos_sin_responsable]
