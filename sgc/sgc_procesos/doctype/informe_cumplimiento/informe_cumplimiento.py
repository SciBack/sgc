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

from sgc.sgc_nucleo.doctype.trazabilidad.trazabilidad import sincronizar_evidencia_enlace

NO_CUMPLE = "No cumple"
PARCIAL = "Cumple parcial"
CUMPLE = "Cumple"


class InformeCumplimiento(Document):
	def validate(self):
		self._autopoblar_condiciones()
		self._consolidar()
		self._validar_sustento()
		self._validar_presentacion()
		self._sincronizar_trazabilidad()

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

	# ------------------------------------------------------------ trazabilidad

	def _sincronizar_trazabilidad(self):
		"""Auto-sincroniza el picklist `evidencia` de cada CBC con Trazabilidad.

		Cada fila `condiciones` (Cumplimiento CBC) trae su propio picklist de
		evidencia (Evidencia Enlace); el destino de la Trazabilidad es la
		`condicion` (Elemento Marco) de esa fila -- sin proceso, porque
		Cumplimiento CBC no lo tiene. Ver `sincronizar_evidencia_enlace` para el
		porqué esto vive en el padre y no en `cumplimiento_cbc.py`.
		"""
		for c in self.condiciones:
			if not c.condicion:
				continue
			# `.get()`, no `.evidencia`: una fila recién construida en memoria
			# (append() con un dict que no trae la clave "evidencia") no tiene
			# ese atributo -- AttributeError con acceso por punto.
			sincronizar_evidencia_enlace(c.get("evidencia"), elemento_marco=c.condicion)

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

	# ------------------------------------------------------------ informe PDF

	@frappe.whitelist()
	def datos_diagnostico(self):
		"""Contrato tipado del informe de diagnóstico CBC (RF-A03).

		Consolida la cabecera + las 8 CBC con su denominación real (del Elemento
		Marco) para que el Print Format solo itere. Único punto de datos del PDF.
		"""
		institucion = (
			frappe.db.get_default("company")
			or frappe.db.get_single_value("System Settings", "app_name")
			or "Universidad Peruana Unión"
		)

		condiciones = []
		for c in self.condiciones:
			em = frappe.db.get_value(
				"Elemento Marco", c.condicion, ["codigo", "denominacion"], as_dict=True
			) or {}
			condiciones.append({
				"codigo": em.get("codigo") or c.condicion,
				"denominacion": em.get("denominacion") or "",
				"cumple": c.cumple or "Sin evaluar",
				"justificacion": c.justificacion or "",
				"no_conformidad": c.no_conformidad or "",
			})

		return {
			"institucion": institucion,
			"anio": self.anio,
			"marco": self.marco_normativo or "",
			"unidad": self.unidad_organica or "",
			"estado": self.estado or "",
			"fecha_presentacion": self.fecha_presentacion,
			"semaforo": self.semaforo or "",
			"n_cumple": self.n_cumple or 0,
			"n_parcial": self.n_parcial or 0,
			"n_no_cumple": self.n_no_cumple or 0,
			"total": len(self.condiciones),
			"condiciones": condiciones,
			"resumen": self.resumen or "",
		}

	@frappe.whitelist()
	def generar_pdf(self, adjuntar=False):
		"""Genera el PDF del diagnóstico CBC (motor Chrome v16). Ver el patrón de
		`sgc.informe.generar_pdf`. Con `adjuntar` truthy lo guarda como File."""
		frappe.local.lang = "es"
		adjuntar = frappe.utils.cint(adjuntar)

		pdf_bytes = frappe.get_print(
			"Informe Cumplimiento",
			self.name,
			print_format="Diagnostico CBC SUNEDU",
			as_pdf=True,
			pdf_generator="chrome",
		)

		if not adjuntar:
			return pdf_bytes

		filedoc = frappe.get_doc({
			"doctype": "File",
			"file_name": "Diagnostico-CBC-{0}.pdf".format(self.name),
			"attached_to_doctype": "Informe Cumplimiento",
			"attached_to_name": self.name,
			"is_private": 1,
			"content": pdf_bytes,
		})
		filedoc.save(ignore_permissions=True)
		frappe.db.set_value("Informe Cumplimiento", self.name, "pdf", filedoc.file_url,
			update_modified=False)
		frappe.db.commit()
		return {"file_name": filedoc.file_name, "file_url": filedoc.file_url}


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
