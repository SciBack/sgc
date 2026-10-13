# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ValoracionEstandar(Document):
	def validate(self):
		"""Bloquea creación/edición si la Autoevaluación padre ya está Cerrada (submit).

		'Valoracion Estandar' es un DocType standalone (Link `autoevaluacion`, no
		child table) -- Frappe NO lo protege automáticamente cuando la Autoevaluacion
		pasa a docstatus=1 vía el workflow nativo (F4). Sin este guard, el snapshot
		del marco quedaría inmutable pero los datos de valoración (incluido el `nivel`
		oficial confirmado por humano) seguirían mutables, contradiciendo el propósito
		de la feature. Va primero en validate() para fallar rápido.

		Esto también bloquea `sgc.confirmacion.confirmar_nivel` tras el cierre --
		correcto: esa función escribe con `ignore_permissions=True` pero el doc pasa
		igual por `validate()`, y confirmar el nivel oficial de un estándar es
		precisamente la acción humana que debe ocurrir ANTES de "Cerrar" (workflow:
		Consolidada -> Cerrar -> Cerrada), nunca después. NO bloquea, en cambio,
		`sgc.confirmacion.finalizar_vigencia`: esa función solo LEE Valoracion
		Estandar y escribe `Autoevaluacion.resultado_vigencia` vía
		`frappe.db.set_value` directo (no pasa por `validate()` de ningún doc) --
		fuera del alcance de este guard; si necesita bloquearse tras el cierre
		también, es responsabilidad del guard en `autoevaluacion.py`/`scoring.py`.
		"""
		if self.autoevaluacion and frappe.db.get_value(
			"Autoevaluacion", self.autoevaluacion, "docstatus"
		) == 1:
			frappe.throw(
				_(
					"La autoevaluación ya fue cerrada y enviada; sus valoraciones "
					"quedan inmutables. Si necesita corregir un dato, cancele y "
					"reabra la autoevaluación (flujo nativo de Frappe: cancel + amend)."
				),
				title=_("Autoevaluación cerrada"),
			)
		self._nivel_solo_via_confirmacion()

	def _nivel_solo_via_confirmacion(self):
		"""El nivel OFICIAL se confirma, no se escribe.

		El permlevel 1 de `nivel` controla QUIÉN puede escribirlo, pero no CÓMO:
		un rol autorizado podía cambiarlo con un save normal, puenteando
		`sgc.confirmacion.confirmar_nivel` — que es donde vive lo que hace de la
		confirmación un acto y no un dato: la traza del override contra lo
		propuesto por el motor, la justificación, `aprobado_por` y el estado.
		Se comprobó en producción: un Responsable de Programa fijó el nivel de
		un estándar con una edición directa, sin dejar ninguna de esas huellas.

		`confirmar_nivel` iza `flags.via_confirmacion` antes de guardar; todo lo
		demás que toque el trío nivel/confirmado/aprobado_por se rechaza. La
		propuesta del motor (`nivel_propuesto`) queda fuera a propósito: proponer
		es del sistema y no necesita ceremonia.
		"""
		if self.flags.get("via_confirmacion"):
			return
		anterior = self.get_doc_before_save()
		campos = ("nivel", "confirmado", "aprobado_por")
		if anterior is None:
			# inserción: el motor crea la fila solo con nivel_propuesto; nacer ya
			# confirmada sería el mismo puenteo con otra puerta.
			mutados = [c for c in campos if self.get(c)]
		else:
			mutados = [c for c in campos if self.get(c) != anterior.get(c)]
		if mutados:
			frappe.throw(
				_(
					"El nivel oficial no se edita directamente ({0}): confírmelo "
					"desde la autoevaluación (sgc.confirmacion.confirmar_nivel), "
					"que registra quién confirma y su justificación."
				).format(", ".join(mutados)),
				title=_("Confirmación requerida"),
			)
