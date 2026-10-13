# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Ficha Indicador — ficha técnica 1:1 con Indicador (o, alternativa CBC, con
Elemento Marco). Fase 2 (2026-07-19, hallazgo): el JSON documentaba "1:1" y
"alternativa" pero no había ninguna validación — nada impedía crear dos fichas
para el mismo indicador, ni una ficha con ambos anclajes (o ninguno) a la vez.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, cint, flt, getdate, nowdate

# Meses entre mediciones según la frecuencia de la ficha. «por_promocion» no
# tiene un calendario fijo: su próxima medición se fija a mano.
MESES_POR_FRECUENCIA = {"mensual": 1, "trimestral": 3, "semestral": 6, "anual": 12}


def fecha_aviso(proxima, dias):
    """El día en que sale el aviso: la próxima medición menos los días de aviso (#92)."""
    if not proxima:
        return None
    return add_days(getdate(proxima), -max(cint(dias), 0))


def avanzar_proxima_medicion(indicador, fecha_valor):
    """Tras registrar un valor, la próxima medición es un periodo después (#92).

    Solo avanza: una medición atrasada que llega tarde no hace retroceder el
    calendario. Se escribe con `db.set_value` para no revalidar la ficha por cada
    valor que entra por la ingesta.
    """
    ficha = frappe.db.get_value(
        "Ficha Indicador", {"indicador": indicador},
        ["name", "frecuencia", "proxima_medicion", "dias_aviso"], as_dict=True,
    )
    if not ficha or ficha.frecuencia not in MESES_POR_FRECUENCIA:
        return
    nueva = add_months(getdate(fecha_valor or nowdate()), MESES_POR_FRECUENCIA[ficha.frecuencia])
    if ficha.proxima_medicion and getdate(ficha.proxima_medicion) >= nueva:
        return
    frappe.db.set_value("Ficha Indicador", ficha.name, {
        "proxima_medicion": nueva,
        "fecha_aviso_medicion": fecha_aviso(nueva, ficha.dias_aviso if ficha.dias_aviso is not None else 7),
    }, update_modified=False)


class FichaIndicador(Document):
    def validate(self):
        if cint(self.dias_aviso) < 0:
            frappe.throw(_("Los días de aviso no pueden ser negativos."))
        self.fecha_aviso_medicion = fecha_aviso(self.proxima_medicion, self.dias_aviso)
        self._validar_participacion()
        if bool(self.indicador) == bool(self.elemento_marco):
            frappe.throw(
                _("La ficha debe anclarse a exactamente uno: «Indicador» "
                  "(fichas CONEAU/institucionales) o «Elemento marco» "
                  "(alternativa para indicadores CBC) — no ambos, no ninguno.")
            )

    def _validar_participacion(self):
        """Peso de cada área en el indicador: sin repetir área, y suman 100 %."""
        filas = self.participacion_areas or []
        if not filas:
            return
        vistas = set()
        for fila in filas:
            if fila.unidad_organica in vistas:
                frappe.throw(_("El área {0} está repetida en la participación.").format(fila.unidad_organica))
            vistas.add(fila.unidad_organica)
            if flt(fila.peso) <= 0:
                frappe.throw(_("El peso de cada área tiene que ser mayor que cero."))
        total = sum(flt(f.peso) for f in filas)
        if abs(total - 100) > 0.01:
            frappe.throw(
                _("Los pesos de las áreas suman {0} %: tienen que sumar 100 %.").format(round(total, 2)),
                title=_("Participación incompleta"),
            )
