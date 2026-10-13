"""Chequeos de los marcos normativos: ¿contra qué se evalúa esta institución? (#50)

Sin ningún marco vigente el sistema funciona, pero no hay estándares contra los
que autoevaluarse ni elementos a los que ligar evidencias: AVISO. Un marco que
sigue «vigente» con su vigencia ya vencida es un marco derogado que aún aparece
en el árbol: también AVISO. Que falte el alcance es INFO: el sistema lo deduce
del ente emisor (`sgc.marcos`), pero mejor declararlo.
"""

import frappe
from frappe.utils import getdate, today

from sgc.verificacion import AVISO, INFO, Hallazgo


def marcos_vigentes():
    vigentes = frappe.get_all(
        "Marco Normativo",
        filters={"estado": "vigente"},
        fields=["name", "alcance", "vigente_hasta"],
        order_by="name asc",
    )
    if not vigentes:
        return [
            Hallazgo(
                AVISO,
                "sin-marcos",
                "No hay ningún marco normativo vigente: no hay estándares contra los que evaluarse.",
                remedio="Cargar los marcos que aplican a la institución (Acreditación y licenciamiento → Marcos normativos).",
            )
        ]

    hoy = getdate(today())
    hallazgos = []
    caducados = [m.name for m in vigentes if m.vigente_hasta and getdate(m.vigente_hasta) < hoy]
    if caducados:
        hallazgos.append(
            Hallazgo(
                AVISO,
                "marco-caducado",
                f"{len(caducados)} marco(s) siguen como vigentes con la vigencia ya terminada.",
                detalle=caducados,
                remedio="Pasarlos a «derogado» o corregir la fecha «vigente hasta».",
            )
        )
    sin_alcance = [m.name for m in vigentes if not m.alcance]
    if sin_alcance:
        hallazgos.append(
            Hallazgo(
                INFO,
                "marco-sin-alcance",
                f"{len(sin_alcance)} marco(s) vigentes sin alcance declarado: se deduce del ente emisor.",
                detalle=sin_alcance,
                remedio="Declarar si es licenciamiento, acreditación de programa, institucional o gestión interna.",
            )
        )
    return hallazgos


CHEQUEOS = [marcos_vigentes]
