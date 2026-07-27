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

Al llegar a "Cerrada" dispara el puente Encuestas -> Indicadores
(`resultado_instrumento.publicar_valores_indicador`): los resultados tabulados
se materializan como `Valor Indicador` (fuente "encuesta") para el motor A2.
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

    def on_update(self):
        """Al quedar Cerrada, publica los indicadores de la encuesta (A2).

        `Aplicacion Instrumento` NO es submittable (los 3 estados del Workflow
        F9 tienen doc_status "0"), así que no hay `on_submit`: el seam es
        `on_update` comprobando el estado, porque `apply_workflow` hace
        `doc.save()` -> validate -> on_update.

        El puente es IDEMPOTENTE, así que re-guardar una aplicación ya cerrada
        simplemente re-publica los mismos valores (y recoge los resultados que
        se hayan cargado después del cierre).
        """
        if self.estado == "Cerrada":
            self._publicar_indicadores()

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

    # ------------------------------------------------- puente -> indicadores
    @frappe.whitelist()
    def publicar_indicadores(self):
        """Re-publica a mano los `Valor Indicador` de esta aplicación.

        Espejo de `tabular()`: mismo seam único, pero de escritura. Existe
        porque el disparo automático ocurre al guardar en estado "Cerrada"; si
        se cargan resultados DESPUÉS del cierre (o se corrige el Indicador
        declarado), Calidad puede re-publicar sin re-transicionar el workflow.
        """
        if self.estado != "Cerrada":
            frappe.throw(
                _("Solo se publican indicadores de una aplicación cerrada "
                  "(estado actual: {0}).").format(self.estado or "-")
            )
        return self._publicar_indicadores()

    def _publicar_indicadores(self):
        from sgc.sgc_gobierno.doctype.resultado_instrumento.resultado_instrumento import (
            publicar_valores_indicador,
        )

        return publicar_valores_indicador(self.name)
