"""La tarea del responsable: el `ToDo` nativo de Frappe como recordatorio (#35).

El seguimiento de una acción es trabajo asignado a alguien con una fecha. Hasta
#35 esa asignación vivía como dos campos dentro del documento (`responsable`,
`fecha_compromiso`) y la persona solo se enteraba si abría el documento. Ahora
el documento le deja una tarea en su lista de pendientes del Desk.

**La frontera, que es lo que hay que respetar:**

    documento (p. ej. Accion Mejora)  — el REGISTRO: estado, evidencia, verificación
          │ genera
          ▼
        ToDo                          — el RECORDATORIO: a quién, para cuándo

Nunca se guarda en el `ToDo` nada que sea evidencia, eficacia o estado del
seguimiento. Cerrar la tarea desde la lista de pendientes no cierra la acción;
es la acción la que, al avanzar, cierra su tarea.

**Por qué no `assign_to.add`.** El alta nativa comparte el documento con quien
lo recibe si este no puede leerlo (`frappe/desk/form/assign_to.py:107-119`), y
compartir exige el permiso «share», que la matriz RBAC del SGC no da a nadie:
guardar una acción con un responsable sin lectura FALLARÍA para la DPGC.
Además, compartir abriría una puerta al documento por fuera de la matriz. Aquí
la tarea se crea sin compartir; si el responsable no puede abrir el documento,
se avisa a quien guarda, que es quien puede corregirlo.

**El aviso.** Se usa el nativo (`notify_assignment`): campana y, si el usuario
lo tiene activado, correo — que pasa por el modo de ensayo y la lista blanca
(`sgc.correo.AvisoDeskSGC`). Frappe no avisa a quien se asigna a sí mismo
(`assign_to.py:279`), y está bien: ya lo sabe, porque lo acaba de hacer.
"""

import frappe
from frappe import _
from frappe.desk.form.assign_to import notify_assignment, set_status

ABIERTA = "Open"
CERRADA = "Closed"
CANCELADA = "Cancelled"


def tareas_abiertas(doctype, name):
	return frappe.get_all(
		"ToDo",
		filters={"reference_type": doctype, "reference_name": name, "status": ABIERTA},
		fields=["name", "allocated_to", "date", "description"],
		order_by="creation",
		limit=0,
	)


def sincronizar(doc, responsable, fecha, descripcion, abierta):
	"""Deja las tareas de `doc` como deben estar. Se puede llamar en cada guardado.

	- `abierta` y con responsable: una tarea abierta suya, con `fecha` como
	  vencimiento. Si cambió el responsable, la del anterior se **cancela** (no la
	  terminó él: dejó de ser suya).
	- no `abierta`: sus tareas abiertas se **cierran** — el trabajo se hizo.
	"""
	actuales = tareas_abiertas(doc.doctype, doc.name)

	for tarea in actuales:
		if not abierta:
			_cambiar_estado(doc, tarea, CERRADA)
		elif tarea.allocated_to != responsable:
			_cambiar_estado(doc, tarea, CANCELADA)
		else:
			cambios = {}
			if str(tarea.date or "") != str(fecha or ""):
				cambios["date"] = fecha
			if (tarea.description or "") != descripcion:
				cambios["description"] = descripcion
			if cambios:
				frappe.db.set_value("ToDo", tarea.name, cambios)

	if abierta and responsable and not any(t.allocated_to == responsable for t in actuales):
		_crear(doc, responsable, fecha, descripcion)


def _cambiar_estado(doc, tarea, estado):
	set_status(
		doc.doctype, doc.name, todo=tarea.name, assign_to=tarea.allocated_to, status=estado, ignore_permissions=True
	)


def _crear(doc, responsable, fecha, descripcion):
	if not frappe.db.get_value("User", responsable, "enabled"):
		return

	frappe.get_doc(
		{
			"doctype": "ToDo",
			"allocated_to": responsable,
			"reference_type": doc.doctype,
			"reference_name": str(doc.name),
			"description": descripcion,
			"date": fecha,
			"status": ABIERTA,
			"priority": "Medium",
			"assigned_by": frappe.session.user,
		}
	).insert(ignore_permissions=True)

	notify_assignment(
		frappe.session.user, responsable, doc.doctype, doc.name, action="ASSIGN", description=descripcion
	)

	if not frappe.has_permission(doc.doctype, "read", doc=doc, user=responsable):
		frappe.msgprint(
			_(
				"{0} tiene la tarea en su lista de pendientes, pero con sus roles actuales no "
				"puede abrir este documento. Revisa sus roles."
			).format(frappe.bold(responsable)),
			indicator="orange",
			alert=True,
		)
