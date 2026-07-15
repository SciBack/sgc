# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""M01 — Diagnóstico de Condiciones Básicas de Calidad (CBC) / IAC.

El Informe de Cumplimiento es el diagnóstico anual del estado de las 8 CBC de
SUNEDU (RF-A01). El controlador:
- auto-puebla las 8 CBC del marco al crear, para no llenarlas a mano (A2);
- consolida el semáforo y los conteos de cumplimiento;
- exige sustento a lo que no cumple y bloquea la presentación con vacíos (A4).

Las 8 CBC son los `Elemento Marco` de tipo Estandar del marco CBC (CBC-I..VIII);
sus componentes (tipo Criterio) cuelgan de cada una en el árbol.
"""

import frappe
from frappe import _
from frappe.model.document import Document

NO_CUMPLE = "No cumple"
PARCIAL = "Cumple parcial"
CUMPLE = "Cumple"


class InformeCumplimiento(Document):
	def validate(self):
		self._autopoblar_condiciones()
		self._consolidar()
		self._validar_sustento()
		self._validar_presentacion()

	# ------------------------------------------------------------ autopoblado

	def _autopoblar_condiciones(self):
		"""Si no hay condiciones y hay marco, carga las 8 CBC (Estandar) del marco."""
		if self.condiciones or not self.marco_normativo:
			return

		cbcs = frappe.get_all(
			"Elemento Marco",
			filters={"marco_normativo": self.marco_normativo, "tipo": "Estandar"},
			fields=["name", "codigo"],
			order_by="orden asc, codigo asc",
		)
		for cbc in cbcs:
			self.append("condiciones", {"condicion": cbc.name})

		if cbcs:
			frappe.msgprint(
				_("Se cargaron {0} CBC del marco {1}. Evalúe cada una.").format(
					len(cbcs), self.marco_normativo
				),
				indicator="blue",
				alert=True,
			)

	# ------------------------------------------------------------ consolidado

	def _consolidar(self):
		"""Cuenta cumplimiento y fija el semáforo global."""
		self.n_cumple = sum(1 for c in self.condiciones if c.cumple == CUMPLE)
		self.n_parcial = sum(1 for c in self.condiciones if c.cumple == PARCIAL)
		self.n_no_cumple = sum(1 for c in self.condiciones if c.cumple == NO_CUMPLE)

		if self.n_no_cumple:
			self.semaforo = "Rojo"
		elif self.n_parcial:
			self.semaforo = "Ámbar"
		elif self.condiciones and self.n_cumple == len(self.condiciones):
			self.semaforo = "Verde"
		else:
			self.semaforo = ""

	# ------------------------------------------------------------ validaciones

	def _validar_sustento(self):
		"""Toda CBC parcial o no cumplida necesita justificación (A4).

		El vínculo a plan de acción/no conformidad se recomienda pero no se
		fuerza aquí: la NC puede abrirse después, en el módulo M05.
		"""
		faltan = [
			c.condicion
			for c in self.condiciones
			if c.cumple in (PARCIAL, NO_CUMPLE) and not (c.justificacion or "").strip()
		]
		if faltan:
			frappe.throw(
				_("Justifique las CBC que no cumplen plenamente: {0}.").format(
					", ".join(faltan)
				),
				title=_("Falta justificación"),
			)

	def _validar_presentacion(self):
		"""No se presenta a SUNEDU con CBC sin evaluar."""
		if self.estado != "Presentado a SUNEDU":
			return

		sin_evaluar = [c.condicion for c in self.condiciones if not c.cumple]
		if sin_evaluar:
			frappe.throw(
				_("No se puede presentar a SUNEDU: hay CBC sin evaluar ({0}).").format(
					", ".join(sin_evaluar)
				),
				title=_("Diagnóstico incompleto"),
			)
		if not self.condiciones:
			frappe.throw(_("No se puede presentar un informe sin condiciones evaluadas."))


@frappe.whitelist()
def cbc_no_cumplidas(informe: str):
	"""CBC en Cumple parcial / No cumple de un informe — insumo para alertar a la
	DPGC y para vincular planes de acción (A4)."""
	doc = frappe.get_doc("Informe Cumplimiento", informe)
	return [
		{
			"condicion": c.condicion,
			"cumple": c.cumple,
			"justificacion": c.justificacion,
			"no_conformidad": c.no_conformidad,
		}
		for c in doc.condiciones
		if c.cumple in (PARCIAL, NO_CUMPLE)
	]
