# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""El cuadro del mapa de procesos: la imagen aprobada, con versión y vigencia.

El SGC ya tiene el mapa como **árbol navegable**, que es lo que sirve para
trabajar. Lo que no tenía es el **cuadro**: la lámina que la institución aprobó
por resolución, con sus colores y su disposición de estratégicos arriba, clave
en medio y soporte abajo. Es lo que la gente reconoce y lo que está colgado en
la pared, y por eso se guarda tal cual en vez de dibujarlo desde el árbol: una
imagen generada se parecería al mapa aprobado, pero no lo sería.

De ahí sale el riesgo propio de esta solución, y el motivo del aviso de desfase:
como la lámina no se regenera, el árbol puede avanzar por debajo y dejarla
obsoleta sin que nadie se entere. `mapa_vigente()` compara la fecha de
aprobación con el último cambio del árbol y lo dice. No bloquea nada —un mapa
aprobado sigue siendo el mapa aprobado aunque el trabajo haya seguido—, pero
deja de ser invisible.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

ESTADO_VIGENTE = "Vigente"
ESTADO_OBSOLETO = "Obsoleto"


class MapaProcesos(Document):
    def validate(self):
        if self.estado != ESTADO_VIGENTE:
            return
        if not self.imagen:
            frappe.throw(_("Un mapa vigente necesita la imagen aprobada."))
        if not self.fecha_aprobacion:
            frappe.throw(_("Un mapa vigente necesita su fecha de aprobación."))

    def on_update(self):
        """Solo puede haber un mapa vigente: los demás quedan obsoletos.

        Se hace aquí y no en `validate` a propósito: si el guardado de este
        documento fallara después, no tendría sentido haber jubilado ya al
        anterior. Y se escribe con `db.set_value` para no disparar el `validate`
        de los otros documentos, que exige imagen y fecha —requisito del mapa
        que entra en vigor, no del que sale—.
        """
        if self.estado != ESTADO_VIGENTE:
            return
        for otro in frappe.get_all(
            "Mapa Procesos",
            filters={"estado": ESTADO_VIGENTE, "name": ["!=", self.name]},
            pluck="name",
        ):
            frappe.db.set_value("Mapa Procesos", otro, "estado", ESTADO_OBSOLETO)


def _ultimo_cambio_arbol():
    """Fecha del cambio más reciente en el árbol de procesos, o None.

    Consulta con `get_list`, así que ve lo que ve quien pregunta. Para alguien
    con el ámbito acotado la fecha puede ser anterior a la real; el aviso sigue
    siendo correcto cuando aparece, solo que puede no aparecer. Es el
    comportamiento que se quiere: antes callar que delatar movimiento en
    unidades que esa persona no puede consultar.
    """
    filas = frappe.get_list(
        "Proceso",
        fields=["modified"],
        order_by="modified desc",
        limit_page_length=1,
    )
    return filas[0].modified if filas else None


@frappe.whitelist()
def mapa_vigente():
    """El mapa institucional en vigor, con el aviso de desfase si lo hay."""
    filas = frappe.get_list(
        "Mapa Procesos",
        filters={"estado": ESTADO_VIGENTE},
        fields=[
            "name",
            "version",
            "titulo",
            "imagen",
            "fecha_aprobacion",
            "aprobado_por",
            "resolucion",
        ],
        limit_page_length=1,
    )
    if not filas:
        return {"hay_mapa": False}

    mapa = filas[0]
    mapa["hay_mapa"] = True
    ultimo_cambio = _ultimo_cambio_arbol()
    mapa["ultimo_cambio_arbol"] = ultimo_cambio
    # Mismo día no es desfase: el árbol suele tocarse justo al cargar el mapa.
    mapa["desfasado"] = bool(
        ultimo_cambio
        and mapa.fecha_aprobacion
        and getdate(ultimo_cambio) > getdate(mapa.fecha_aprobacion)
    )
    return mapa
