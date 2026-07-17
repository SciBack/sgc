# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M12 — Aplicación de Instrumento.

Representa la aplicación concreta de un `Instrumento` a un grupo de interés en
un periodo académico y ámbito (unidad orgánica / programa-sede). Gobierna el
ciclo de campo de la encuesta mediante el Select `estado`:

    Planificada -> En campo -> Cerrada

y por eso lleva Workflow nativo (`sgc/setup/f9_workflow_encuestas.py`). Las
validaciones son INCREMENTALES por etapa (mismo patrón que No Conformidad, M05):
cada estado exige, de forma acumulativa, lo que esa etapa requiere.
"""
import frappe
from frappe import _
from frappe.model.document import Document

# Orden del ciclo de vida (coincide con el Workflow "Aplicacion Instrumento SGC").
# Se usa para exigir de forma incremental lo que cada etapa requiere.
ORDEN = {
    "Planificada": 0,
    "En campo": 1,
    "Cerrada": 2,
}


class AplicacionInstrumento(Document):
    def validate(self):
        self._validar_coherencia_muestral()
        self._validar_fechas()
        self._calcular_tasa_respuesta()
        self._validar_por_etapa()

    # ------------------------------------------------------------------ helpers
    def _validar_coherencia_muestral(self):
        """La muestra no puede exceder la población declarada."""
        if self.poblacion and self.muestra and self.muestra > self.poblacion:
            frappe.throw(
                _("La muestra ({0}) no puede ser mayor que la población ({1}).").format(
                    self.muestra, self.poblacion
                )
            )

    def _validar_fechas(self):
        """La fecha de fin no puede ser anterior a la de inicio."""
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            frappe.throw(
                _("La fecha de fin no puede ser anterior a la fecha de inicio.")
            )

    def _calcular_tasa_respuesta(self):
        """Deriva la tasa de respuesta desde el conteo de LimeSurvey.

        Respuestas / base * 100, donde la base es la muestra (o, en su defecto,
        la población). El conteo de la plataforma es la fuente autoritativa, así
        que recalcula el campo cuando hay conteo y base. Se acota a 100 %.
        """
        base = self.muestra or self.poblacion
        if self.limesurvey_response_count and base:
            self.tasa_respuesta = round(
                min(self.limesurvey_response_count * 100.0 / base, 100.0), 2
            )

    def _validar_por_etapa(self):
        """Exigencias acumulativas según el estado del ciclo de campo."""
        nivel = ORDEN.get(self.estado, 0)

        # A partir de "En campo": debe tener definida la fecha de inicio del campo.
        if nivel >= 1 and not self.fecha_inicio:
            frappe.throw(
                _("Define la fecha de inicio antes de poner la aplicación en campo.")
            )

        # Al "Cerrar": debe tener fecha de fin del campo (para acotar el periodo
        # de recolección y poder tabular resultados con un corte definido).
        if nivel >= 2 and not self.fecha_fin:
            frappe.throw(
                _("Registra la fecha de fin antes de cerrar la aplicación.")
            )

    # -------------------------------------------------------------- tabulación
    @frappe.whitelist()
    def tabular(self):
        """Devuelve la tabulación agregada de esta aplicación (para un tablero).

        Seam único de consumo: delega en `resultado_instrumento.tabular_aplicacion`.
        """
        from sgc.sgc_gobierno.doctype.resultado_instrumento.resultado_instrumento import (
            tabular_aplicacion,
        )

        return tabular_aplicacion(self.name)
