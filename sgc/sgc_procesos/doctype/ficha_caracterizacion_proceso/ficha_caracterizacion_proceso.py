# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""M03 — Ficha de Caracterización de Proceso (SIPOC + PHVA).

La ficha es el documento que caracteriza un `Proceso` del Mapa de Procesos y,
en su bloque "Verificar / Actuar", DECLARA los indicadores de desempeño de ese
proceso (child `Indicador Proceso Link` → Link a `Indicador`).

Este controlador es el único punto donde esa declaración se vuelve dato
consultable: sincroniza en ambos sentidos el enlace explícito
`ficha.indicadores[] ↔ Indicador.proceso`, que es lo que permite al motor
`sgc.indicadores_proceso` responder "qué indicadores tiene este proceso" sin
inferir nada por texto libre.

Distinción que exige el objetivo específico 3 (indicador de proceso vs.
indicador de acreditación): el discriminador es explícito y doble —
`Indicador.marco_normativo` no vacío ⇒ es de acreditación (el loader CONEAU lo
setea siempre); `Indicador.proceso` no vacío ⇒ es de proceso. Un indicador de
acreditación NO puede declararse aquí (ver `_validar_indicadores`).
"""

import frappe
from frappe import _
from frappe.model.document import Document

# Valor de `Indicador.categoria` que marca un indicador de desempeño de proceso.
CATEGORIA_PROCESO = "Proceso"


class FichaCaracterizacionProceso(Document):
	def validate(self):
		self._validar_indicadores()

	def on_update(self):
		# La sincronización escribe en OTRO doctype (`Indicador`), así que va
		# después de que la ficha esté persistida: si el save falla, no queda
		# ningún indicador apuntando a una ficha que no existe.
		self._sincronizar_indicadores()

	def on_trash(self):
		"""Al borrar la ficha, ningún indicador queda apuntando a este proceso."""
		self._limpiar_indicadores_huerfanos(declarados=set())

	# ------------------------------------------------------------ validaciones

	def _validar_indicadores(self):
		"""Reglas duras de la declaración de indicadores de la ficha.

		1. Sin duplicados dentro de la misma ficha.
		2. Ningún indicador de acreditación (`marco_normativo` no vacío): es la
		   única forma de distinguirlos sin adivinar por texto libre.
		3. Ningún indicador ya declarado por la ficha de otro proceso: un
		   indicador de desempeño pertenece a UN proceso (si no, `Indicador.proceso`
		   —que es un Link simple— no podría representar la relación).
		"""
		vistos = set()
		duplicados = []
		acreditacion = []

		for fila in self.indicadores:
			if not fila.indicador:
				continue
			if fila.indicador in vistos:
				duplicados.append(fila.indicador)
				continue
			vistos.add(fila.indicador)

			if frappe.db.get_value("Indicador", fila.indicador, "marco_normativo"):
				acreditacion.append(fila.indicador)

		if duplicados:
			frappe.throw(
				_("Hay indicadores repetidos en la ficha: {0}.").format(
					", ".join(sorted(set(duplicados)))
				),
				title=_("Indicadores duplicados"),
			)

		if acreditacion:
			frappe.throw(
				_(
					"Estos indicadores pertenecen a un marco normativo (son indicadores "
					"de acreditación) y no pueden declararse como indicadores de "
					"desempeño de un proceso: {0}."
				).format(", ".join(sorted(set(acreditacion)))),
				title=_("Indicador de acreditación"),
			)

		self._validar_no_declarado_en_otra_ficha(vistos)

	def _validar_no_declarado_en_otra_ficha(self, declarados):
		"""Un indicador no puede estar declarado en dos fichas a la vez."""
		if not declarados:
			return

		filas = frappe.get_all(
			"Indicador Proceso Link",
			filters={
				"indicador": ["in", list(declarados)],
				"parenttype": "Ficha Caracterizacion Proceso",
				"parentfield": "indicadores",
				"parent": ["!=", self.name],
			},
			fields=["indicador", "parent"],
		)
		if filas:
			detalle = ", ".join(
				"{0} (ya en {1})".format(f["indicador"], f["parent"]) for f in filas
			)
			frappe.throw(
				_("Estos indicadores ya están declarados en otra ficha: {0}.").format(detalle),
				title=_("Indicador ya asignado"),
			)

	# ---------------------------------------------------------- sincronización

	def _sincronizar_indicadores(self):
		"""Refleja la declaración de la ficha en `Indicador` (idempotente).

		Idempotente en el sentido del repo: se lee el estado actual y solo se
		escribe lo que difiere; correrlo N veces deja el mismo resultado.

		Se escribe con `frappe.db.set_value(..., update_modified=False)` para no
		ensuciar el historial del `Indicador` ni disparar hooks en cascada: el
		dato de negocio (quién declara qué) vive en la ficha; en el indicador
		esto es solo el índice inverso.
		"""
		declarados = {f.indicador for f in self.indicadores if f.indicador}

		for codigo in declarados:
			actual = frappe.db.get_value(
				"Indicador", codigo, ["proceso", "categoria"], as_dict=True
			)
			if not actual:
				# Link roto (el Indicador se borró entre validate y on_update):
				# no se inventa nada, lo reportará el motor lector como omitido.
				continue

			cambios = {}
			if actual.get("proceso") != self.proceso:
				cambios["proceso"] = self.proceso
			if actual.get("categoria") != CATEGORIA_PROCESO:
				cambios["categoria"] = CATEGORIA_PROCESO
			if cambios:
				frappe.db.set_value("Indicador", codigo, cambios, update_modified=False)

		self._limpiar_indicadores_huerfanos(declarados)

	def _limpiar_indicadores_huerfanos(self, declarados):
		"""Quita `Indicador.proceso` a los que ya no declara esta ficha.

		Solo toca indicadores cuyo `proceso` es EXACTAMENTE el proceso de esta
		ficha: nunca se pisa la declaración de otro proceso. No se toca
		`categoria` — que el indicador deje de colgar de un proceso no lo
		convierte automáticamente en otra cosa; eso lo decide quien lo edite.
		"""
		if not self.proceso:
			return

		huerfanos = frappe.get_all(
			"Indicador",
			filters={"proceso": self.proceso},
			pluck="name",
		)
		for codigo in huerfanos:
			if codigo in declarados:
				continue
			frappe.db.set_value("Indicador", codigo, "proceso", None, update_modified=False)
