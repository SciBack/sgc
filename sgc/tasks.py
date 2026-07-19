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
