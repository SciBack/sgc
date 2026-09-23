"""Conserva el envío real en los sitios que ya mandaban correo (#41).

Desde #41 el modo por defecto es Ensayo: un sitio nuevo no escribe a nadie hasta
que un administrador lo decide. Pero un sitio que YA enviaba —porque alguien
pasó sus reglas a canal Email a mano— tomó esa decisión antes de que existiera
el interruptor. Si la actualización lo dejara en ensayo, los avisos que hoy
reciben personas reales dejarían de llegar sin error ni aviso: el corte
silencioso que una actualización no debe provocar.

Así que: si ya hay alguna regla de correo activa, el modo queda en Real, sin
lista blanca, igual que antes. Si no la hay, queda en Ensayo. En ambos casos lo
dice en la salida del migrate. Solo actúa si el modo aún no se ha fijado.
"""

import frappe


def execute():
	frappe.reload_doc("sgc_nucleo", "doctype", "configuracion_correo")

	if frappe.db.get_single_value("Configuracion Correo", "modo"):
		return

	reglas = frappe.get_all("Notification", filters={"channel": "Email", "enabled": 1}, pluck="name", limit=0)
	modo = "Real" if reglas else "Ensayo"
	frappe.db.set_single_value("Configuracion Correo", "modo", modo)

	if reglas:
		print(
			f"Configuracion Correo: modo Real conservado — el sitio ya enviaba correo "
			f"con {len(reglas)} regla(s): {', '.join(sorted(reglas))}."
		)
	else:
		print("Configuracion Correo: modo Ensayo — no había reglas de correo activas.")
