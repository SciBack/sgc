"""Acuse de lectura de los documentos publicados (ISO 9001 §7.3 y §7.4).

ISO 9001 pide que las personas conozcan la política de calidad y los documentos que les
aplican, y conservar evidencia de ello. Hasta ahora el SGC solo avisaba al publicar
(`Documento Controlado.difundir_a`): sabía a quién se le había dicho, no quién lo había
leído.

Cómo funciona:

- El documento marca **«Pedir acuse de lectura»**. Al publicarse, se crea un `Acuse
  Lectura` *Pendiente* por cada persona de «Difundir también a» y para el dueño del
  proceso, con una tarea (ToDo) que cuelga del acuse. No cuelga del documento: el
  documento ya sincroniza su propia tarea de revisión, y esa sincronización cerraría
  cualquier otra tarea abierta suya.
- La persona abre su acuse y pulsa **«Confirmar lectura»**: declara que lo leyó y, si el
  documento trae preguntas de comprensión, las responde. El servidor califica: la
  respuesta correcta tiene `permlevel` 1 y no llega nunca al navegador de quien acusa
  (`frappe/model/document.py::apply_fieldlevel_read_permissions`). El patrón viene de
  Frappe LMS (`lms_quiz.py`), que tampoco se fía de la nota que manda el navegador.
- Un acuse es de una **versión**: si el documento vuelve a borrador o se publica una
  versión nueva, los pendientes quedan *Sin efecto* y se piden de nuevo al publicar.

Nadie crea ni edita un acuse a mano: no hay permiso de crear ni de escribir. Solo este
módulo los escribe, así que un acuse no se puede fabricar.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, now_datetime, nowdate

from sgc import tareas

PENDIENTE = "Pendiente"
ACUSADO = "Acusado"
SIN_EFECTO = "Sin efecto"

# Plazo de la tarea para confirmar la lectura.
DIAS_PARA_ACUSAR = 15
LETRAS = ("A", "B", "C", "D")
PUBLICADO = "Publicado"


def destinatarios(doc):
	"""Quién debe acusar: «Difundir también a» y el dueño del proceso, sin repetir y activos."""
	usuarios = [fila.usuario for fila in doc.get("difundir_a") or [] if fila.usuario]
	if doc.get("dueno_proceso"):
		usuarios.append(doc.dueno_proceso)
	usuarios = list(dict.fromkeys(usuarios))
	if not usuarios:
		return []
	activos = set(frappe.get_all("User", filters={"name": ["in", usuarios], "enabled": 1}, pluck="name"))
	return [u for u in usuarios if u in activos]


def pendiente_de(doc, usuario=None):
	"""El acuse pendiente de esta versión del documento para el usuario, o None."""
	return frappe.db.get_value(
		"Acuse Lectura",
		{"documento": doc.name, "version": doc.version, "usuario": usuario or frappe.session.user, "estado": PENDIENTE},
	)


def al_cambiar_estado(doc, anterior):
	"""Se llama desde `on_update` del documento.

	Al dejar de estar publicado, los pendientes quedan sin efecto. Al publicarse, se dejan
	sin efecto los de versiones anteriores y se piden los de esta.
	"""
	if anterior == PUBLICADO and doc.estado != PUBLICADO:
		_dejar_sin_efecto(doc.name)
	elif doc.estado == PUBLICADO and anterior != PUBLICADO:
		_dejar_sin_efecto(doc.name, salvo_version=doc.version)
		if doc.requiere_acuse:
			_pedir(doc)


def _pedir(doc):
	ya_pedidos = set(
		frappe.get_all("Acuse Lectura", filters={"documento": doc.name, "version": doc.version}, pluck="usuario")
	)
	descripcion = _("Confirmar la lectura de {0} «{1}», versión {2}").format(doc.codigo or doc.name, doc.titulo, doc.version)
	fecha = add_days(nowdate(), DIAS_PARA_ACUSAR)
	for usuario in destinatarios(doc):
		if usuario in ya_pedidos:
			continue
		acuse = frappe.get_doc({
			"doctype": "Acuse Lectura",
			"documento": doc.name,
			"version": doc.version,
			"usuario": usuario,
			"estado": PENDIENTE,
		}).insert(ignore_permissions=True)
		# Frappe pone de owner a quien crea el registro (`document.py::set_user_and_timestamp`), y
		# la lectura de «Desk User» es `if_owner`: el acuse tiene que ser de quien debe leer.
		acuse.db_set("owner", usuario, update_modified=False)
		tareas.sincronizar(acuse, usuario, fecha, descripcion, abierta=True)


def _dejar_sin_efecto(documento, salvo_version=None):
	filtros = {"documento": documento, "estado": PENDIENTE}
	if salvo_version is not None:
		filtros["version"] = ["!=", salvo_version]
	for nombre in frappe.get_all("Acuse Lectura", filters=filtros, pluck="name"):
		acuse = frappe.get_doc("Acuse Lectura", nombre)
		acuse.estado = SIN_EFECTO
		acuse.save(ignore_permissions=True)
		# Cancelada, no cerrada: la persona no hizo nada, dejó de tocarle.
		tareas.sincronizar_por_responsable(acuse, {}, terminados=())


def _acuse_propio(nombre):
	acuse = frappe.get_doc("Acuse Lectura", nombre)
	if acuse.usuario != frappe.session.user:
		frappe.throw(_("Este acuse de lectura es de otra persona."), frappe.PermissionError)
	return acuse


def _documento_vigente(acuse):
	doc = frappe.get_doc("Documento Controlado", acuse.documento)
	if not frappe.has_permission("Documento Controlado", "read", doc=doc):
		frappe.throw(_("No tiene acceso a este documento."), frappe.PermissionError)
	if doc.estado != PUBLICADO or cint(doc.version) != cint(acuse.version):
		frappe.throw(_("El documento cambió desde que se le pidió el acuse: ya no está publicado en la versión {0}.")
					 .format(acuse.version))
	return doc


def _preguntas(documento, campos):
	return frappe.get_all(
		"Pregunta Acuse",
		filters={"parent": documento, "parenttype": "Documento Controlado", "parentfield": "preguntas_acuse"},
		fields=campos,
		order_by="idx asc",
	)


@frappe.whitelist()
def preguntas(acuse):
	"""Lo que necesita el diálogo de «Confirmar lectura», **sin** las respuestas correctas."""
	acuse = _acuse_propio(acuse)
	doc = _documento_vigente(acuse)
	filas = _preguntas(doc.name, ["idx", "pregunta", "opcion_a", "opcion_b", "opcion_c", "opcion_d"])
	return {
		"documento": doc.name,
		"titulo": doc.titulo,
		"version": doc.version,
		"nota_minima": flt(doc.nota_minima_acuse),
		"preguntas": [
			{
				"idx": f.idx,
				"pregunta": f.pregunta,
				"opciones": [[letra, f.get(f"opcion_{letra.lower()}")] for letra in LETRAS if f.get(f"opcion_{letra.lower()}")],
			}
			for f in filas
		],
	}


@frappe.whitelist()
def acusar(acuse, respuestas=None, declaro=0):
	"""Registra el acuse. Con preguntas, califica en el servidor y exige la nota mínima.

	`respuestas`: {idx de la pregunta: letra}. Devuelve si quedó aprobado y la nota, pero no
	cuáles fallaron: sería darle la respuesta para el siguiente intento.
	"""
	acuse = _acuse_propio(acuse)
	if acuse.estado != PENDIENTE:
		frappe.throw(_("Este acuse ya no está pendiente."))
	doc = _documento_vigente(acuse)
	if not cint(declaro):
		frappe.throw(_("Marque la declaración de que leyó y entendió el documento."))

	claves = _preguntas(doc.name, ["idx", "correcta"])
	acuse.intentos = cint(acuse.intentos) + 1
	acuse.declaracion = 1
	resultado = {"aprobado": True, "puntaje": None, "nota_minima": flt(doc.nota_minima_acuse), "aciertos": None,
				 "total": len(claves)}
	if claves:
		respuestas = frappe.parse_json(respuestas) or {}
		aciertos = sum(1 for c in claves if (respuestas.get(str(c.idx)) or "") == c.correcta)
		acuse.puntaje = round(100 * aciertos / len(claves), 1)
		resultado.update(puntaje=acuse.puntaje, aciertos=aciertos, aprobado=acuse.puntaje >= flt(doc.nota_minima_acuse))

	if resultado["aprobado"]:
		acuse.estado = ACUSADO
		acuse.fecha_acuse = now_datetime()
	acuse.save(ignore_permissions=True)
	if resultado["aprobado"]:
		tareas.sincronizar_por_responsable(acuse, {}, terminados=None)
	return resultado
