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
		self._traer_evidencias_esperadas()
		self._valorar_por_evidencias()

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

	# ------------------------------------------------------- por evidencias

	def _traer_evidencias_esperadas(self):
		"""Una fila por evidencia que el criterio pide (`Elemento Marco.evidencias_esperadas`).

		Idempotente por código: añade las que falten (un marco al que se le cargan evidencias después
		también llega a las autoevaluaciones en curso) y nunca borra una fila ya valorada.
		"""
		if not self.criterio:
			return
		esperadas = frappe.get_all(
			"Evidencia Esperada",
			filters={"parent": self.criterio, "parenttype": "Elemento Marco", "parentfield": "evidencias_esperadas"},
			fields=["codigo", "descripcion"], order_by="idx asc",
		)
		ya = {fila.codigo for fila in self.get("evidencias_valoradas") or []}
		for e in esperadas:
			if e.codigo not in ya:
				self.append("evidencias_valoradas", {"codigo": e.codigo, "descripcion": e.descripcion})

	def _valorar_por_evidencias(self):
		"""Cada evidencia se valora por su % y, con todas valoradas, el criterio se valora solo.

		Regla de la matriz de autoevaluación de la institución piloto (25-nov-2026), umbrales en
		`site_config` (`scoring.umbrales`): ≥ logrado → Logrado; > en proceso → En proceso; resto, No
		logrado. Una fila está **pendiente** mientras su avance sea 0 sin «no aplica» ni brecha escrita:
		Frappe guarda un % vacío como 0, y un 0 % real se registra explicando la brecha.

		El criterio pasa a Cumple / Cumple parcial / No cumple con el promedio de sus evidencias (sin las
		que no aplican), o a No aplica si ninguna aplica, para que el nivel del estándar, la vigencia y el
		informe sigan funcionando igual. Sin evidencias esperadas, el juicio sigue siendo manual.
		"""
		filas = self.get("evidencias_valoradas") or []
		if not filas:
			return
		from sgc.scoring import valoracion_por_avance

		pendientes = 0
		for fila in filas:
			if fila.no_aplica:
				fila.valoracion = "No aplica"
			elif not fila.avance and not (fila.observacion or "").strip():
				fila.valoracion = "Pendiente"
				pendientes += 1
			else:
				fila.valoracion = valoracion_por_avance(fila.avance)

		aplicables = [f for f in filas if not f.no_aplica]
		self.avance_criterio = (sum(f.avance or 0 for f in aplicables) / len(aplicables)) if aplicables else 0
		if pendientes:
			self.cumple = ""
		elif not aplicables:
			self.cumple = "No aplica"
		else:
			self.cumple = {"Logrado": "Cumple", "En proceso": "Cumple parcial"}.get(
				valoracion_por_avance(self.avance_criterio), "No cumple")

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
		# Y la evidencia aportada en cada fila de «Evidencias esperadas»: mismo destino (el criterio).
		sincronizar_evidencia_enlace(self.get("evidencias_valoradas"), elemento_marco=self.criterio)

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
		from sgc.scoring import _calcular_avance_pct, proponer_nivel_estandar

		proponer_nivel_estandar(self.autoevaluacion, estandar)
		# El avance se ve durante la autoevaluación, no solo al cerrarla: antes solo se
		# recalculaba al confirmar todos los estándares y marcaba 0 % todo el proceso.
		frappe.db.set_value(
			"Autoevaluacion", self.autoevaluacion, "avance_pct",
			_calcular_avance_pct(self.autoevaluacion), update_modified=False,
		)
