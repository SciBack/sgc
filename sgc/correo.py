"""Correo de las reglas de notificación: ensayo, lista blanca y destinatarios (#41).

Encender el correo en un sistema en producción es empezar a escribir a personas
reales. Los dos fallos posibles no los detecta ningún test:

- **Escribir de más**: el primer envío alcanza a gente que no esperaba nada.
- **No escribir a nadie**: el rol destinatario no tiene usuarios con correo, el
  sistema no falla, y todos creen que los avisos funcionan.

Contra lo primero, dos interruptores en `Configuracion Correo`: el **modo**
(Ensayo / Real) y la **lista blanca de estreno**. Contra lo segundo,
`comprobar_destinatarios`, que dice cuántas personas alcanza cada regla.

**Dónde se intercepta.** Hay dos caminos de correo, y los dos pasan por aquí:

1. Las **reglas** (`Notification`). Los workflows tienen `send_email_alert=0` y
   el código no llama a `sendmail`. `Notification.send_an_email` resuelve los
   destinatarios con `get_list_of_recipients` y, si queda alguno, envía; si no
   queda ninguno, sale sin enviar ni crear la Communication
   (frappe/email/doctype/notification/notification.py:496-507). Por eso basta
   con filtrar ahí —solo durante el envío de correo, nunca para la campana del
   Desk—.
2. La **campana** (`Notification Log`). Cada aviso del Desk manda además su
   propio correo con `frappe.sendmail` si el tipo lo tiene activado
   (notification_log.py:64): asignaciones, menciones, documentos compartidos.
   Los de las reglas (tipo `Alert`) no, porque Frappe los excluye
   (`notification_skip_email_types`). Hasta #35 nadie asignaba tareas de
   forma automática y este camino no se usaba; desde que la acción de mejora
   asigna la suya al responsable, sí. Lo filtra `AvisoDeskSGC`.

Lo que se quita no se envía, y se anota en `Registro Correo`.

**Sin configurar, el modo es Ensayo.** Un sitio nuevo no escribe a nadie hasta
que un administrador lo decide. Los sitios que ya enviaban antes de esta versión
conservan el envío real: lo fija el parche `correo_conservar_envio_real`.
"""

import re

import frappe
from frappe.desk.doctype.notification_log.notification_log import (
	NotificationLog,
	set_notifications_as_unseen,
)
from frappe.desk.doctype.notification_settings.notification_settings import (
	is_email_notifications_enabled_for_type,
)
from frappe.email.doctype.notification.notification import Notification
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


# --- intercepción --------------------------------------------------------------


class NotificacionSGC(Notification):
	"""`Notification` que respeta el modo de ensayo y la lista blanca.

	Se registra en `override_doctype_class`. Solo filtra mientras se envía un
	CORREO: Frappe usa el mismo `get_list_of_recipients` para la campana del
	Desk (`create_system_notification`, notification.py:468), y el ensayo no
	debe apagar los avisos internos. Tampoco basta con mirar `self.channel`:
	una regla de canal Email con `send_system_notification` pasa por los dos
	caminos, y solo el del correo se filtra.
	"""

	def send_an_email(self, doc, context):
		self._filtrando_correo = True
		try:
			return super().send_an_email(doc, context)
		finally:
			self._filtrando_correo = False

	def get_list_of_recipients(self, doc, context):
		para, cc, cco = super().get_list_of_recipients(doc, context)
		if not getattr(self, "_filtrando_correo", False):
			return para, cc, cco
		a_enviar, registros = decidir({"Para": para, "CC": cc, "CCO": cco}, modo(), lista_blanca())
		if registros:
			_registrar(self, doc, context, registros)
		return a_enviar["Para"], a_enviar["CC"], a_enviar["CCO"]


def _asunto(regla, context):
	asunto = regla.subject or ""
	if "{" in asunto:
		try:
			asunto = frappe.render_template(asunto, context)
		except Exception:
			pass  # el registro no debe impedir que la regla termine
	return asunto


def _registrar(regla, doc, context, registros):
	asunto = _asunto(regla, context)
	for correo, tipo, resultado in registros:
		_anotar(correo, tipo, resultado, asunto, doc.doctype, doc.name, regla=regla.name)


def _anotar(correo, tipo, resultado, asunto, documento_tipo, documento, regla=None, aviso=None):
	frappe.get_doc(
		{
			"doctype": "Registro Correo",
			"resultado": resultado,
			"destinatario": correo,
			"tipo": tipo,
			"regla": regla,
			"aviso": aviso,
			"asunto": asunto,
			"documento_tipo": documento_tipo,
			"documento": documento,
		}
	).insert(ignore_permissions=True)


class AvisoDeskSGC(NotificationLog):
	"""`Notification Log` cuyo correo respeta el modo de ensayo y la lista blanca.

	Se registra en `override_doctype_class`. La campana se crea siempre: lo que
	se filtra es solo el correo que la acompaña. Si el tipo de aviso no manda
	correo (`Alert`, o el usuario lo desactivó), no hay nada que decidir y no se
	anota nada: `Registro Correo` es de correos que habrían salido.

	El camino sin correo repite las dos líneas de `NotificationLog.after_insert`
	que no son el envío (notification_log.py:62-63). Si Frappe cambia ese
	método, esta copia se queda atrás sin avisar: lo vigila
	`test_correo.test_el_aviso_del_desk_sigue_el_after_insert_de_frappe`.
	"""

	def after_insert(self):
		if not is_email_notifications_enabled_for_type(self.for_user, self.type):
			return super().after_insert()

		correo = frappe.db.get_value("User", self.for_user, "email")
		a_enviar, registros = decidir({"Para": [correo]}, modo(), lista_blanca())
		if a_enviar["Para"]:
			return super().after_insert()

		asunto = strip_html(self.subject or "")
		for destinatario, tipo, resultado in registros:
			_anotar(
				destinatario, tipo, resultado, asunto, self.document_type, self.document_name, aviso=self.type
			)
		frappe.publish_realtime("notification", after_commit=True, user=self.for_user)
		set_notifications_as_unseen(self.for_user)


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
