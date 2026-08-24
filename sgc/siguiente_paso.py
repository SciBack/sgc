# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""De quién es el turno en un documento con ciclo de vida.

`frappe.model.workflow.get_transitions` devuelve solo **mis** acciones: si el
documento está esperando a otro rol, devuelve una lista vacía y la pantalla dice
«no hay acciones disponibles». Eso es cierto y es inútil — la pregunta de quien
mira no es «¿puedo hacer algo?» sino «¿y ahora qué pasa con esto?».

Comprobado usando el sistema el 2026-08-24: se crea un documento, se envía a
revisión, y la persona se queda ante una pantalla que no dice si tiene que
esperar, a quién, ni cuánto. En un flujo con segregación de funciones —donde por
diseño la siguiente acción es de OTRA persona— eso pasa en la mitad de los pasos.

Aquí se devuelven **todas** las transiciones posibles desde el estado actual, con
su rol, marcando cuáles son mías. La lógica de quién puede ejecutar qué sigue
siendo del motor: esto solo la hace legible.
"""

import frappe


@frappe.whitelist()
def de(doctype: str, name: str) -> dict:
	"""Estado actual y qué puede pasar a continuación, para quien sea.

	Devuelve:
	  - `estado`: el estado en que está el documento.
	  - `mias`: acciones que esta persona puede ejecutar ahora.
	  - `de_otros`: las que existen pero corresponden a otro rol, con el rol.
	  - `final`: True si el documento no tiene salida (terminó su ciclo).
	"""
	if not frappe.has_permission(doctype, "read", doc=name):
		frappe.throw(frappe._("Sin permiso para consultar este documento."))

	workflow = frappe.db.get_value(
		"Workflow", {"document_type": doctype, "is_active": 1},
		["name", "workflow_state_field"], as_dict=True,
	)
	if not workflow:
		return {"estado": None, "mias": [], "de_otros": [], "final": False}

	estado = frappe.db.get_value(doctype, name, workflow.workflow_state_field)
	transiciones = frappe.get_all(
		"Workflow Transition",
		filters={"parent": workflow.name, "state": estado},
		fields=["action", "next_state", "allowed"],
		order_by="idx",
	)

	mis_roles = set(frappe.get_roles())
	mias, de_otros = [], []
	for t in transiciones:
		destino = {"accion": t.action, "estado_destino": t.next_state, "rol": t.allowed}
		(mias if t.allowed in mis_roles else de_otros).append(destino)

	return {
		"estado": estado,
		"mias": mias,
		"de_otros": de_otros,
		# Sin transiciones de salida el documento terminó: eso también es una
		# respuesta, y bastante mejor que el silencio.
		"final": not transiciones,
	}
