# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from sgc.sgc_acreditacion.doctype.trazabilidad.trazabilidad import sincronizar_evidencia_enlace


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

		self._validar_unica()

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

	def _validar_unica(self):
		"""Un criterio se valora una sola vez por autoevaluación: dos valoraciones darían dos juicios."""
		otra = frappe.db.get_value("Valoracion Criterio", {
			"autoevaluacion": self.autoevaluacion, "criterio": self.criterio, "name": ["!=", self.name or ""]})
		if otra:
			frappe.throw(_("El criterio {0} ya tiene su valoración en esta autoevaluación: {1}.").format(
				frappe.bold(self.criterio), frappe.get_desk_link("Valoracion Criterio", otra)))

	def _sincronizar_tarea(self):
		"""El responsable del criterio tiene una tarea hasta que el criterio queda valorado (`sgc/tareas.py`)."""
		from sgc import tareas

		ae = frappe.db.get_value("Autoevaluacion", self.autoevaluacion, ["titulo", "fecha_cierre"], as_dict=True) or {}
		descripcion = _("Valorar el criterio {0} de «{1}»").format(self.criterio, ae.get("titulo") or self.autoevaluacion)
		tareas.sincronizar(self, self.responsable, ae.get("fecha_cierre"), descripcion, abierta=not self.cumple)

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
		self._sincronizar_tarea()
		if self.flags.preparada_al_iniciar:
			return  # nace sin juicio: no hay nada que recalcular

		estandar = frappe.db.get_value(
			"Elemento Marco", self.criterio, "parent_elemento_marco"
		)
		if not estandar:
			return

		# Import diferido para evitar ciclos en el arranque de Frappe.
		from sgc.scoring import proponer_nivel_estandar

		proponer_nivel_estandar(self.autoevaluacion, estandar)
