"""Retira el módulo vacío «SGC UPeU» (#65, canónico sin nombre de cliente).

El canónico nació con un módulo que llevaba el nombre del cliente alfa. Nunca
tuvo DocTypes, informes ni páginas: era una carpeta vacía con su `Module Def`.
Al salir de `modules.txt`, Frappe deja de crearlo en los sitios nuevos, pero en
los existentes el `Module Def` sigue ahí, huérfano.

Este parche lo borra SOLO si nada lo referencia. Si algo cuelga de él —un
informe o una personalización hecha a mano en el sitio—, no se toca y lo dice en
la salida del migrate: perder una personalización por limpiar un nombre sería
peor que conservar el nombre.
"""

import frappe

MODULO = "SGC UPeU"


def execute():
	if not frappe.db.exists("Module Def", MODULO):
		return
	try:
		frappe.delete_doc("Module Def", MODULO, ignore_permissions=True)
	except frappe.LinkExistsError:
		print(f"Module Def «{MODULO}»: se conserva, hay registros que lo usan.")
		return
	print(f"Module Def «{MODULO}»: retirado (no lo usaba nada).")
