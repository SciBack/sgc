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
	# El "is set" NO es redundante: el constructor de consultas envuelve la
	# comparacion en IFNULL(campo, '0001-01-01'), asi que una evidencia SIN fecha
	# de vigencia se compara como si fuera del año 1 y sale siempre "vencida".
	# `vigencia_hasta` es opcional a proposito —un acta o un reglamento no
	# caducan—, de modo que sin este filtro el job marcaba Vencida toda evidencia
	# que no declarara vencimiento, y ademas sin dejar rastro en el historial.
	vencidas = frappe.get_all(
		"Evidencia",
		filters=[
			["estado", "in", ("Pendiente", "Valida")],
			["vigencia_hasta", "is", "set"],
			["vigencia_hasta", "<", getdate(nowdate())],
		],
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
	# Mismo motivo que en las evidencias: sin el "is set", un acuerdo sin fecha
	# de compromiso se leeria como vencido el dia que corra el job.
	vencidos = frappe.get_all(
		"Acuerdo",
		filters=[
			["estado", "in", ("Pendiente", "En proceso")],
			["fecha_compromiso", "is", "set"],
			["fecha_compromiso", "<", getdate(nowdate())],
		],
		pluck="name",
	)
	for name in vencidos:
		frappe.db.set_value("Acuerdo", name, "estado", "Vencido", update_modified=False)

	frappe.db.commit()
