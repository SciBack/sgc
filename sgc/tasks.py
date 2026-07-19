# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Tareas programadas (scheduler_events) del app.

Cubren el gap de `Evidencia.on_update` (`_marcar_vencida_si_expiro`, ver
sgc/sgc_nucleo/doctype/evidencia/evidencia.py): ese flip solo corre cuando
alguien guarda el documento, así que una Evidencia cuya `vigencia_hasta`
expiró y a la que nadie vuelve a tocar queda "Pendiente"/"Valida" para
siempre. Este job cierra ese gap recorriendo la tabla directamente.
"""

import frappe
from frappe.utils import getdate, nowdate


def marcar_evidencias_vencidas():
	"""Marca Vencida toda Evidencia Pendiente/Valida cuya vigencia ya expiró.

	Mismo patrón que `Evidencia._marcar_vencida_si_expiro`: escribe con
	`frappe.db.set_value(..., update_modified=False)` en vez de
	`doc.estado = "Vencida"; doc.save()` porque el workflow nativo
	`Evidencia SGC` (f13) bloquea, a nivel de motor, cualquier transición que
	no esté en su grafo -- y "Vencida" es intencionalmente un estado que solo
	pone el sistema, no una transición humana.
	"""
	vencidas = frappe.get_all(
		"Evidencia",
		filters={
			"estado": ["in", ("Pendiente", "Valida")],
			"vigencia_hasta": ["<", getdate(nowdate())],
		},
		pluck="name",
	)
	for name in vencidas:
		frappe.db.set_value("Evidencia", name, "estado", "Vencida", update_modified=False)

	frappe.db.commit()


def marcar_acuerdos_vencidos():
	"""Marca Vencido todo Acuerdo Pendiente/En proceso cuya fecha_compromiso ya pasó.

	Cierra el mismo gap que `marcar_evidencias_vencidas`: `Acuerdo.validate()`
	solo actúa al guardar -- si nadie vuelve a tocar un acuerdo tras vencer,
	se queda "Pendiente"/"En proceso" para siempre. Acuerdo no tiene Workflow
	nativo, así que `frappe.db.set_value` es solo por consistencia con el
	patrón del módulo, no por necesidad de bypass de motor.
	"""
	vencidos = frappe.get_all(
		"Acuerdo",
		filters={
			"estado": ["in", ("Pendiente", "En proceso")],
			"fecha_compromiso": ["<", getdate(nowdate())],
		},
		pluck="name",
	)
	for name in vencidos:
		frappe.db.set_value("Acuerdo", name, "estado", "Vencido", update_modified=False)

	frappe.db.commit()
