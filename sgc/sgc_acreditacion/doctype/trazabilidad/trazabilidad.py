# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Trazabilidad — vínculo N:M entre una Evidencia y un elemento del marco y/o un
proceso (M09).

Es el mecanismo canónico que el Informe de Autoevaluación (sgc.informe) consume
para listar qué evidencias respaldan cada estándar/criterio. Una evidencia puede
tener varias Trazabilidad (a criterio, a CBC, a proceso — RNF09); un elemento se
sustenta en varias evidencias.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class Trazabilidad(Document):
	def validate(self):
		# Un vínculo que no apunta a nada no traza nada.
		if not self.elemento_marco and not self.proceso:
			frappe.throw(
				_("La Trazabilidad debe vincular la evidencia a un elemento del "
				  "marco, a un proceso, o a ambos."),
				title=_("Vínculo vacío"),
			)

		# Evitar duplicar el mismo vínculo (misma evidencia al mismo destino).
		# Un Link vacío se guarda como NULL en Postgres, y NULL no matchea "" en un
		# filtro de igualdad → hay que buscarlo con "is not set", no con or "".
		filtros = {"evidencia": self.evidencia, "name": ["!=", self.name or ""]}
		filtros["elemento_marco"] = self.elemento_marco if self.elemento_marco else ["is", "not set"]
		filtros["proceso"] = self.proceso if self.proceso else ["is", "not set"]
		if frappe.db.exists("Trazabilidad", filtros):
			frappe.throw(
				_("Ya existe una Trazabilidad de esta evidencia hacia el mismo destino."),
				title=_("Vínculo duplicado"),
			)


def sincronizar_evidencia_enlace(filas_evidencia_enlace, elemento_marco=None, proceso=None):
	"""Auto-sincroniza un picklist `Evidencia Enlace` (Table MultiSelect) con Trazabilidad.

	`Cumplimiento CBC` (vía `Informe Cumplimiento`) y `Hallazgo Auditoria` exponen
	un campo `evidencia` como Table MultiSelect de `Evidencia Enlace` -- un
	picklist rápido, no el vínculo N:M oficial. Sin este sync, una evidencia
	adjuntada solo por ese picklist queda invisible para el Informe de
	Autoevaluación (informe.py) y no cuenta para el gate
	`Evidencia._validar_trazabilidad_si_valida` (hallazgo de la investigación de
	brecha Evidencia Enlace / Trazabilidad).

	Idempotente vía `frappe.db.exists()` -- mismo patrón que
	`sgc.capa.escalar_a_no_conformidad`: no duplica si la Trazabilidad ya existe.
	No crea nada si faltan AMBOS destinos (`elemento_marco` y `proceso`), porque
	`Trazabilidad.validate()` rechazaría ese vínculo vacío.

	Los llamadores van en el `validate()` de cada DOCUMENTO PADRE real (no en el
	controlador de una child table `istable:1`: Frappe nunca invoca el
	`validate()` de una fila de child table -- las persiste con
	`Document.update_child_table()` -> `d.db_update()` directo, sin pasar por
	`run_method("validate")`).
	"""
	if not elemento_marco and not proceso:
		return

	for fila in filas_evidencia_enlace or []:
		# `.get()`, no `getattr()`: una fila de un Table MultiSelect construida
		# en memoria (nested dentro de OTRA child table, vía append() con un
		# dict) llega como dict plano, no como Document -- getattr() no lee
		# claves de dict. `.get()` funciona igual para dict y para Document
		# (BaseDocument también expone `.get()`).
		evidencia = fila.get("evidencia") if hasattr(fila, "get") else None
		if not evidencia:
			continue

		filtros = {
			"evidencia": evidencia,
			"elemento_marco": elemento_marco if elemento_marco else ["is", "not set"],
			"proceso": proceso if proceso else ["is", "not set"],
		}
		if frappe.db.exists("Trazabilidad", filtros):
			continue

		vals = {"doctype": "Trazabilidad", "evidencia": evidencia, "origen": "Auto-sincronizado"}
		if elemento_marco:
			vals["elemento_marco"] = elemento_marco
		if proceso:
			vals["proceso"] = proceso
		frappe.get_doc(vals).insert(ignore_permissions=True)
