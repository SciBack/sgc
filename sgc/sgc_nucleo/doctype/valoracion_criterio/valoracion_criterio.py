# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from sgc.sgc_nucleo.doctype.trazabilidad.trazabilidad import sincronizar_evidencia_enlace


class ValoracionCriterio(Document):
	def validate(self):
		"""Bloquea creación/edición si la Autoevaluación padre ya está Cerrada (submit).

		'Valoracion Criterio' es un DocType standalone (Link `autoevaluacion`, no
		child table) -- Frappe NO lo protege automáticamente cuando la Autoevaluacion
		pasa a docstatus=1 vía el workflow nativo (F4). Sin este guard, el snapshot
		del marco quedaría inmutable pero los datos de valoración seguirían mutables,
		contradiciendo el propósito de la feature. Va primero en validate() para
		fallar rápido, antes de cualquier otra validación de negocio.
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

		# El estado operativo se deriva del juicio y nunca de una selección del
		# navegador. Así una escritura genérica no puede declarar una valoración
		# revisada o valorada sin haber registrado el resultado correspondiente.
		self.estado = "Valorado" if self.cumple else "Pendiente"
		if not self.cumple:
			self.valorado_por = None
			self.fecha = None
		elif self.is_new() or self.has_value_changed("cumple"):
			self.valorado_por = frappe.session.user
			self.fecha = now_datetime()

		# Último paso: va DESPUÉS del guard de autoevaluación cerrada, para que
		# una autoevaluación ya cerrada no pueda generar Trazabilidad nueva.
		self._sincronizar_trazabilidad()

	# ------------------------------------------------------------ trazabilidad

	def _sincronizar_trazabilidad(self):
		"""Auto-sincroniza el picklist `evidencia` con Trazabilidad (RNF09).

		Este es el enganche del flujo de AUTOEVALUACIÓN hacia Trazabilidad, que
		es lo que `sgc.informe._evidencias_de_elementos` consulta para listar
		las evidencias de cada estándar (filtra `elemento_marco in (estándar +
		sus criterios)`). Sin esto, una evidencia vinculada al valorar un
		criterio queda invisible para el informe de autoevaluación y no cuenta
		para el gate `Evidencia._validar_trazabilidad_si_valida`.

		Destino: solo `elemento_marco` = el criterio valorado. `Valoracion
		Criterio` no tiene proceso ni forma explícita de derivarlo (el criterio
		es un `Elemento Marco`, no un proceso) y NO se infiere: se deja el
		vínculo solo al elemento, que `Trazabilidad.validate()` acepta.

		Aditivo, igual que en `Informe Cumplimiento` y `Hallazgo Auditoria`:
		desvincular una evidencia del picklist NO borra la Trazabilidad ya
		creada; para retirarla del informe hay que borrar la Trazabilidad.
		"""
		if not self.criterio:
			return
		# `.get()`, no `.evidencia`: si el DocType aún no migró en el entorno
		# (campo nuevo), el acceso por punto reventaría; así degrada a None.
		sincronizar_evidencia_enlace(self.get("evidencia"), elemento_marco=self.criterio)

	def on_update(self):
		"""Al valorar un criterio, recomputar el nivel propuesto de su estándar.

		El estándar padre del criterio es el `parent_elemento_marco` del criterio
		(criterio depth 3 -> estándar depth 2). El motor solo escribe `nivel_propuesto`
		en la Valoracion Estandar; el `nivel` oficial lo confirma el humano.

		Llamada directa (no enqueue): en F2 el recomputo de un estándar es liviano.
		"""
		if not self.autoevaluacion or not self.criterio:
			return

		estandar = frappe.db.get_value(
			"Elemento Marco", self.criterio, "parent_elemento_marco"
		)
		if not estandar:
			return

		# Import diferido para evitar ciclos en el arranque de Frappe.
		from sgc.scoring import proponer_nivel_estandar

		proponer_nivel_estandar(self.autoevaluacion, estandar)
