# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M12 — Instrumento.

Define un instrumento de escucha (encuesta de satisfacción, focus group,
entrevista o buzón) dirigido a un grupo de interés y, opcionalmente, ligado a
un indicador (A1) al que sus resultados tributan. La plataforma por defecto es
LimeSurvey (integración RemoteControl2 vía `limesurvey_survey_id`).

El DocType no tiene campo `estado` de flujo → NO lleva Workflow. La validación
asegura coherencia entre la plataforma y su puntero al survey.
"""
import frappe
from frappe import _
from frappe.model.document import Document


class Instrumento(Document):
    def validate(self):
        if self.codigo:
            self.codigo = self.codigo.strip()
        if self.nombre:
            self.nombre = self.nombre.strip()

        # El puntero a LimeSurvey solo tiene sentido si la plataforma es LimeSurvey.
        # Si el instrumento se declara en "Otra" plataforma, se descarta el survey_id
        # para no dejar un puntero colgante que la integración interpretaría mal.
        if self.plataforma == "Otra" and self.limesurvey_survey_id:
            self.limesurvey_survey_id = None

        # Coherencia inversa: si es LimeSurvey pero sin survey_id, es una definición
        # incompleta que la sincronización no podrá resolver. Se avisa (no se bloquea:
        # el instrumento puede registrarse antes de crear el survey en LimeSurvey).
        if (
            self.plataforma == "LimeSurvey"
            and not (self.limesurvey_survey_id or "").strip()
        ):
            frappe.msgprint(
                _("Instrumento en LimeSurvey sin survey_id: la sincronización de "
                  "respuestas quedará pendiente hasta asignarlo."),
                indicator="orange",
                alert=True,
            )
