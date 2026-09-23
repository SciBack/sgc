"""Pasa a correo las reglas del SGC que nacieron solo en la campana (#29).

Hasta #29 el canónico creaba sus `Notification` con canal `System Notification`
y cada institución las pasaba a Email a mano. Desde #29 las declara `Email` con
campana (`send_system_notification=1`), pero `f7`/`f15` solo fijan el canal al
CREAR: `Notification.channel` tiene `set_only_once=1` y un `save()` que lo cambia
lanza CannotChangeConstantError. Por eso este parche lo escribe directo en la
base, una vez, en las reglas del SGC (prefijo «SGC - »). A las que ya eran de
correo solo les devuelve la campana, que perdieron al pasarlas a mano.

Qué correo sale de verdad no lo decide este parche sino `Configuracion Correo`
(#41), que va antes en patches.txt: en Ensayo no se escribe a nadie. En un sitio
en Real, las reglas que pasan a correo empiezan a enviar desde este despliegue,
y por eso las nombra en la salida del migrate.
"""

import frappe

PREFIJO = "SGC - "


def execute():
	reglas = frappe.get_all(
		"Notification",
		filters={"name": ["like", PREFIJO + "%"]},
		fields=["name", "channel", "send_system_notification"],
		order_by="name",
		limit=0,
	)

	a_correo = []
	for regla in reglas:
		cambios = {}
		if regla.channel == "System Notification":
			cambios["channel"] = "Email"
			a_correo.append(regla.name)
		if not regla.send_system_notification:
			cambios["send_system_notification"] = 1
		if cambios:
			frappe.db.set_value("Notification", regla.name, cambios, update_modified=False)

	# `run_notifications` lee las reglas de una caché por DocType.
	frappe.clear_cache()

	if a_correo:
		modo = frappe.db.get_single_value("Configuracion Correo", "modo") or "Ensayo"
		print(
			f"Notificaciones: {len(a_correo)} regla(s) pasan a correo (modo {modo}): "
			f"{', '.join(a_correo)}."
		)
