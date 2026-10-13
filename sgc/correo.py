"""Correo de las reglas de notificación: ensayo, lista blanca y destinatarios (#41).

Encender el correo en un sistema en producción es empezar a escribir a personas
reales. Los dos fallos posibles no los detecta ningún test:

- **Escribir de más**: el primer envío alcanza a gente que no esperaba nada.
- **No escribir a nadie**: el rol destinatario no tiene usuarios con correo, el
  sistema no falla, y todos creen que los avisos funcionan.

Contra lo primero, dos interruptores en `Configuracion Correo`: el **modo**
(Ensayo / Real) y la **lista blanca de estreno**. Contra lo segundo,
`comprobar_destinatarios`, que dice cuántas personas alcanza cada regla.

**Dónde se intercepta.** En la cola de correo de Frappe (`Email Queue`), con un
`doc_events` estándar: por ahí pasa todo correo, venga de una regla, de la
campana del Desk o de un envío a demanda. Hasta la 1.0.1 se interceptaba
sobrescribiendo las clases `Notification` y `Notification Log`, y Frappe 16.50
cambió la firma de `send_an_email`: cada aviso fallaba en silencio. Un gancho
sobre la cola no depende de esas clases.

Lo que se quita no se envía, y se anota en `Registro Correo`.

**Sin configurar, el modo es Ensayo.** Un sitio nuevo no escribe a nadie hasta
que un administrador lo decide. Los sitios que ya enviaban antes de esta versión
conservan el envío real: lo fija el parche `correo_conservar_envio_real`.
"""

import re

import frappe
from frappe.utils import strip_html

ENSAYO = "Ensayo"
REAL = "Real"

NO_ENVIADO = "No enviado (ensayo)"
OMITIDO = "Omitido (fuera de lista blanca)"

# Frappe descarta estas dos al resolver un rol (frappe/core/doctype/role/role.py:114).
_CUENTAS_FICTICIAS = {"admin@example.com", "guest@example.com"}


# --- decisión (pura) -----------------------------------------------------------


def normalizar_lista(texto):
	"""Direcciones de la lista blanca, en minúsculas y sin repetir.

	Acepta una por línea, pero también comas, punto y coma o espacios: quien la
	rellena pega lo que tiene a mano.
	"""
	vistas = []
	for parte in re.split(r"[\s,;]+", texto or ""):
		correo = parte.strip().lower()
		if correo and correo not in vistas:
			vistas.append(correo)
	return vistas


def decidir(destinatarios, modo, lista_blanca):
	"""Qué se envía y qué se registra. No toca la base.

	`destinatarios`: {"Para": [...], "CC": [...], "CCO": [...]}.
	Devuelve (a_enviar, registros): `a_enviar` con la misma forma, `registros`
	una lista de (correo, tipo, resultado) para lo que no sale.

	Cualquier modo que no sea exactamente «Real» se trata como ensayo: ante un
	valor raro o ausente, lo seguro es no escribir.
	"""
	blanca = {c.lower() for c in lista_blanca or []}
	a_enviar = {tipo: [] for tipo in destinatarios}
	registros = []

	for tipo, correos in destinatarios.items():
		for correo in correos:
			if not correo:
				continue
			if modo != REAL:
				registros.append((correo, tipo, NO_ENVIADO))
			elif blanca and correo.strip().lower() not in blanca:
				registros.append((correo, tipo, OMITIDO))
			else:
				a_enviar[tipo].append(correo)

	return a_enviar, registros


# --- configuración -------------------------------------------------------------


def modo():
	return frappe.db.get_single_value("Configuracion Correo", "modo") or ENSAYO


def lista_blanca():
	return normalizar_lista(frappe.db.get_single_value("Configuracion Correo", "lista_blanca"))


# --- intercepción: la cola de correo de Frappe ------------------------------------


def filtrar_cola(doc, method=None):
	"""`doc_events` de «Email Queue», en `before_insert`: el único punto de control.

	Todo correo que Frappe envía —reglas, campana del Desk, envíos a demanda,
	restablecer contraseña— entra en la cola con `EmailQueue.new`, que hace un
	`insert` normal (frappe/email/doctype/email_queue/email_queue.py:104-117).
	Filtrar aquí no depende de cómo Frappe arme cada correo: es un gancho
	estándar sobre un DocType estándar, y sobrevive a las actualizaciones.

	Hace dos cosas:

	1. **Adjuntos de solo consulta (#36).** Un documento que solo se consulta en
	   pantalla no viaja adjunto por correo; tampoco un adjunto sin fichero.
	2. **Modo y lista blanca (#41).** Quita los destinatarios no autorizados y
	   los anota en `Registro Correo`. Si no queda ninguno, el correo queda en
	   «Error» con el motivo: la cola solo envía lo que está «Not Sent» o
	   «Partially Sent» (frappe/email/queue.py:174), así que no se reintenta solo.
	"""
	_quitar_adjuntos_de_solo_consulta(doc)

	en_copia = {c.lower() for c in normalizar_lista(doc.show_as_cc)}
	destinos = {"Para": [], "CC": []}
	for fila in doc.recipients:
		destinos["CC" if fila.recipient.lower() in en_copia else "Para"].append(fila.recipient)

	a_enviar, registros = decidir(destinos, modo(), lista_blanca())
	if not registros:
		return

	autorizados = {c.lower() for correos in a_enviar.values() for c in correos}
	doc.set("recipients", [f for f in doc.recipients if f.recipient.lower() in autorizados])
	asunto = asunto_del_mensaje(doc.message)
	for correo, tipo, resultado in registros:
		_anotar(correo, tipo, resultado, asunto, doc.reference_doctype, doc.reference_name)

	if not doc.recipients:
		doc.status = "Error"
		doc.error = f"Retenido por el SGC: {registros[0][2]}. Ver Registro Correo."


def _quitar_adjuntos_de_solo_consulta(doc):
	if not doc.attachments:
		return
	adjuntos = frappe.parse_json(doc.attachments) or []
	solo_consulta = doc.reference_doctype == "Documento Controlado" and frappe.db.get_value(
		"Documento Controlado", doc.reference_name, "solo_consulta"
	)

	def es_fichero(a):
		return isinstance(a, dict) and ("fid" in a or "file_url" in a)

	quedan = [
		a
		for a in adjuntos
		if not (es_fichero(a) and (solo_consulta or not (a.get("fid") or a.get("file_url"))))
	]
	if len(quedan) != len(adjuntos):
		doc.attachments = frappe.as_json(quedan)


def asunto_del_mensaje(mensaje):
	"""El asunto, legible, de un mensaje MIME tal como lo guarda la cola."""
	from email import message_from_string
	from email.header import decode_header, make_header

	try:
		crudo = message_from_string(mensaje or "").get("Subject") or ""
		return strip_html(str(make_header(decode_header(crudo))))
	except Exception:
		return ""


def _anotar(correo, tipo, resultado, asunto, documento_tipo, documento, aviso=None):
	frappe.get_doc(
		{
			"doctype": "Registro Correo",
			"resultado": resultado,
			"destinatario": correo,
			"tipo": tipo,
			"aviso": aviso,
			"asunto": asunto,
			"documento_tipo": documento_tipo,
			"documento": documento,
		}
	).insert(ignore_permissions=True)


# --- envíos a demanda (#92) ------------------------------------------------------

_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def es_correo(texto):
	return bool(_CORREO.match((texto or "").strip()))


def enviar(para, asunto, mensaje, documento_tipo=None, documento=None, origen=None,
		   adjuntos=None, formato_impresion=None):
	"""Envío a demanda (no una regla): el único camino de los envíos nuevos.

	Aplica el mismo modo y la misma lista blanca que las reglas (#41): lo que no
	sale se anota en `Registro Correo`. Lo que sale va por `Communication`, así
	queda en el historial del documento. Se usa `_make` y no `make` porque `make`
	exige el permiso «email», que la matriz no reparte: quien llama a esta función
	ya ha comprobado quién puede enviar qué.

	Devuelve {"enviados": [...], "retenidos": [(correo, resultado), ...]}.
	"""
	from frappe.core.doctype.communication.email import _make

	vistos = []
	for correo in para or []:
		c = (correo or "").strip()
		if c and c.lower() not in {v.lower() for v in vistos}:
			vistos.append(c)

	a_enviar, registros = decidir({"Para": vistos}, modo(), lista_blanca())
	for correo, tipo, resultado in registros:
		_anotar(correo, tipo, resultado, asunto, documento_tipo, documento, aviso=origen)

	if a_enviar["Para"]:
		_make(
			doctype=documento_tipo,
			name=documento,
			subject=asunto,
			content=mensaje,
			recipients=a_enviar["Para"],
			send_email=1,
			attachments=adjuntos or None,
			print_format=formato_impresion,
			communication_type="Communication",
		)
	return {"enviados": a_enviar["Para"], "retenidos": [(c, r) for c, _t, r in registros]}


# --- comprobación previa de destinatarios -------------------------------------


def _correos_del_rol(rol):
	"""Los correos que Frappe usará para un rol: usuarios habilitados con correo."""
	usuarios = frappe.get_all("Has Role", filters={"role": rol, "parenttype": "User"}, pluck="parent", limit=0)
	if not usuarios:
		return []
	correos = frappe.get_all(
		"User",
		filters={"name": ["in", usuarios], "enabled": 1},
		pluck="email",
		limit=0,
	)
	return sorted({c for c in correos if c and c.lower() not in _CUENTAS_FICTICIAS})


def comprobar_destinatarios():
	"""Para cada regla de correo activa, a quién puede alcanzar.

	Los destinatarios por rol se cuentan; los que salen de un campo del
	documento solo se pueden nombrar, porque dependen de cada documento.
	"""
	blanca = set(lista_blanca())
	reglas = frappe.get_all(
		"Notification",
		filters={"channel": "Email", "enabled": 1},
		fields=["name", "document_type"],
		order_by="name",
		limit=0,
	)
	resultado = []
	for regla in reglas:
		filas = frappe.get_all(
			"Notification Recipient",
			filters={"parent": regla.name, "parenttype": "Notification"},
			fields=["receiver_by_role", "receiver_by_document_field", "cc", "bcc"],
			order_by="idx",
			limit=0,
		)
		destinos = []
		for fila in filas:
			if fila.receiver_by_role:
				correos = _correos_del_rol(fila.receiver_by_role)
				destinos.append(
					{
						"tipo": "rol",
						"valor": fila.receiver_by_role,
						"correos": correos,
						"en_lista_blanca": sorted(c for c in correos if c.lower() in blanca),
					}
				)
			if fila.receiver_by_document_field:
				destinos.append({"tipo": "campo", "valor": fila.receiver_by_document_field})
			for tipo, texto in (("cc", fila.cc), ("cco", fila.bcc)):
				if texto:
					destinos.append({"tipo": tipo, "valor": texto})
		resultado.append({"regla": regla.name, "documento": regla.document_type, "destinos": destinos})
	return resultado


def roles_sin_destinatarios(reglas=None):
	"""(regla, rol) de los roles destinatarios que no alcanzan a nadie."""
	reglas = comprobar_destinatarios() if reglas is None else reglas
	return [
		(r["regla"], d["valor"])
		for r in reglas
		for d in r["destinos"]
		if d["tipo"] == "rol" and not d["correos"]
	]


@frappe.whitelist()
def estado():
	"""Lo que muestra el formulario de Configuracion Correo. Solo System Manager."""
	frappe.only_for("System Manager")
	reglas = comprobar_destinatarios()
	return {
		"modo": modo(),
		"lista_blanca": lista_blanca(),
		"reglas": reglas,
		"roles_vacios": roles_sin_destinatarios(reglas),
	}
