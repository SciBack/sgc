"""Valoración de la atención por quien reclamó (ISO 9001 §9.1.2).

ISO 9001 pide seguir la percepción del cliente sobre si se cumplieron sus necesidades. El
momento más claro es cuando se cierra su reclamo, y hasta ahora el SGC no preguntaba nada.

- La salida no conforme que viene de un **reclamo** guarda el correo de quien reclamó.
- Al **cerrarse**, se crea una `Web Form Request` (nativa de Frappe) con una clave de un solo
  uso que caduca a los 15 días, y se le envía el enlace al formulario web «valoracion-atencion».
  La salida no conforme viaja en `doc_values`: la fija el servidor, no el formulario, así que
  el reclamante no puede valorar otra cosa. Frappe valida la clave, su caducidad y su uso
  único (`web_form_request.py::validate_key`), y limita los envíos por minuto.
- El enlace **no** se guarda en el historial de la salida no conforme: el correo se envía sin
  referencia al documento. Si se guardara, cualquiera que pudiera leer el registro podría usar
  el enlace y valorar en nombre del reclamante. Queda constancia en «Valoración solicitada» y
  en el Registro de correo.
- El envío pasa por `sgc.correo.enviar`, con el modo y la lista blanca de la instancia: si la
  lista blanca lo retiene, no se marca como solicitada y se avisa a quien cerró.

El patrón viene de Frappe Helpdesk (encuesta al cerrar el ticket), con la pieza nativa que
Helpdesk reimplementa a mano: la clave de un solo uso de `Web Form Request`.
"""

import frappe
from frappe import _
from frappe.utils import add_days, get_url, now_datetime

from sgc import correo
from sgc.identidad import sgc_identidad

FORMULARIO = "valoracion-atencion"
DIAS_PARA_VALORAR = 15
ORIGEN_RECLAMO = "Reclamo de usuario"


def pedir(salida):
	"""Pide la valoración al cerrarse una salida no conforme que vino de un reclamo con correo."""
	destino = (salida.get("correo_reclamante") or "").strip()
	if salida.origen != ORIGEN_RECLAMO or not destino or salida.get("valoracion_solicitada"):
		return None

	solicitud = frappe.get_doc({
		"doctype": "Web Form Request",
		"web_form": FORMULARIO,
		"expires_on": add_days(now_datetime(), DIAS_PARA_VALORAR),
		"doc_values": frappe.as_json({"salida_no_conforme": salida.name}),
	}).insert(ignore_permissions=True)
	enlace = get_url(f"/{FORMULARIO}/new?web_form_request_key={solicitud.key}")

	institucion = sgc_identidad().institucion
	asunto = _("¿Cómo atendimos su reclamo?")
	mensaje = _(
		"<p>Su reclamo «{0}» se atendió y se cerró.</p>"
		"<p>¿Nos dice cómo lo hicimos? Le toma un minuto y nos ayuda a mejorar:</p>"
		'<p><a href="{1}">Valorar la atención</a></p>'
		"<p>El enlace sirve una sola vez y caduca en {2} días.</p>"
		"<p>{3}</p>"
	).format(frappe.utils.escape_html(salida.titulo), enlace, DIAS_PARA_VALORAR, frappe.utils.escape_html(institucion))

	# Sin documento de referencia a propósito: ver el docstring del módulo.
	resultado = correo.enviar([destino], asunto, mensaje, origen=_("Valoración de la atención"))
	if resultado["enviados"]:
		salida.db_set("valoracion_solicitada", now_datetime(), update_modified=False)
	else:
		frappe.msgprint(
			_("No se pidió la valoración a {0}: el correo de la instancia lo retuvo (modo de ensayo o lista "
			  "blanca).").format(destino),
			indicator="orange",
			alert=True,
		)
	return resultado
