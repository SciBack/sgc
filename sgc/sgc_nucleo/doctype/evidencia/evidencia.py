# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""M09 — Repositorio de evidencias de acreditación/licenciamiento.

Una evidencia es un archivo (o enlace) verificable que respalda el cumplimiento
de uno o más elementos del marco normativo (criterios, estándares, condiciones
CBC) y/o procesos del Mapa.

El vínculo evidencia<->elemento/proceso es N:M y se modela con el DocType
`Trazabilidad` (evidencia + elemento_marco/proceso + tipo_vinculo + origen), que
es el mecanismo canónico que ya consume el Informe de Autoevaluación (informe.py).
Desde la ficha de Evidencia se ven/crean sus Trazabilidad vía la sección
Connections (bloque `links` del DocType). RNF09 (vincular a la vez a proceso +
CBC + estándar) se cubre con varias Trazabilidad sobre la misma evidencia.

El controlador: autocompleta los metadatos técnicos desde el archivo adjunto,
exige al menos una traza para dar una evidencia por válida, y marca como Vencida
la evidencia cuya vigencia expiró.
"""

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate


class Evidencia(Document):
	def before_insert(self):
		if not self.codigo:
			self.codigo = self._generar_codigo()
		if not self.cargado_por:
			self.cargado_por = frappe.session.user
		if not self.fecha_carga:
			self.fecha_carga = now_datetime()

	def validate(self):
		self._sincronizar_metadatos_archivo()
		self._marcar_vencida_si_expiro()
		self._validar_soporte()
		self._validar_trazabilidad_si_valida()

	# ---------------------------------------------------------------- helpers

	def _generar_codigo(self) -> str:
		"""Código EVD-AAAA-NNNN, correlativo por año de carga.

		Correlativo = máximo sufijo existente + 1 (no count): con count, borrar
		una evidencia intermedia haría reusar un número y chocar con el `unique`.
		"""
		anio = getdate(nowdate()).year
		existentes = frappe.get_all(
			"Evidencia", filters={"codigo": ["like", f"EVD-{anio}-%"]}, pluck="codigo"
		)
		maximo = 0
		for c in existentes:
			m = re.search(r"(\d+)$", c or "")
			if m:
				maximo = max(maximo, int(m.group(1)))
		return f"EVD-{anio}-{maximo + 1:04d}"

	def _sincronizar_metadatos_archivo(self):
		"""Copia MIME, tamaño y hash desde el File adjunto (fuente única de verdad).

		Frappe ya guardó el binario y calculó su content_hash al subirlo; aquí solo
		lo reflejamos en la Evidencia para poder filtrar/reportar sin abrir el File.
		"""
		if not self.archivo:
			# Sin archivo no hay metadatos técnicos que sostener.
			self.mime = self.tamano = self.hash_sha256 = None
			return

		archivo_doc = frappe.db.get_value(
			"File",
			{"file_url": self.archivo},
			["file_size", "content_hash", "file_type"],
			as_dict=True,
		)
		if not archivo_doc:
			return

		self.tamano = archivo_doc.file_size
		self.hash_sha256 = archivo_doc.content_hash
		if archivo_doc.file_type:
			self.mime = archivo_doc.file_type.lower()

	def _marcar_vencida_si_expiro(self):
		if self.vigencia_hasta and getdate(self.vigencia_hasta) < getdate(nowdate()):
			if self.estado in ("Pendiente", "Valida"):
				self.estado = "Vencida"

	def _validar_soporte(self):
		"""Toda evidencia necesita un soporte: archivo, o URL si es de tipo Enlace."""
		if self.tipo == "Enlace":
			if not self.enlace_url:
				frappe.throw(_("Una evidencia de tipo Enlace requiere la URL."))
		elif not self.archivo:
			frappe.throw(_("Adjunte el archivo de la evidencia (o cambie el tipo a Enlace)."))

	def _validar_trazabilidad_si_valida(self):
		"""Una evidencia no puede darse por Válida sin estar anclada a algo.

		La norma exige que la evidencia sea verificable y trazable al elemento que
		respalda; una evidencia válida "colgando de nada" no sirve para auditoría.
		El vínculo vive en Trazabilidad, que apunta a esta evidencia — por eso se
		crea DESPUÉS de guardar la evidencia (primero Pendiente, se vincula, y
		recién entonces se puede marcar Válida).
		"""
		if self.estado != "Valida" or self.is_new():
			return

		if not frappe.db.exists("Trazabilidad", {"evidencia": self.name}):
			frappe.throw(
				_("Para marcar la evidencia como Válida, cree al menos una "
				  "Trazabilidad que la vincule a un elemento del marco "
				  "(criterio / estándar / CBC) o a un proceso."),
				title=_("Falta trazabilidad"),
			)


@frappe.whitelist()
def evidencias_de_elemento(elemento_marco: str):
	"""Evidencias que respaldan un elemento del marco (criterio/estándar/CBC).

	Consulta inversa del vínculo N:M (vía Trazabilidad) — la que usa la ficha de un
	criterio para mostrar "¿qué evidencias lo sustentan?".
	"""
	nombres = frappe.get_all(
		"Trazabilidad",
		filters={"elemento_marco": elemento_marco},
		pluck="evidencia",
	)
	nombres = list({n for n in nombres if n})
	if not nombres:
		return []

	return frappe.get_all(
		"Evidencia",
		filters={"name": ["in", nombres]},
		fields=["name", "codigo", "titulo", "tipo", "estado", "archivo"],
		order_by="codigo",
	)
