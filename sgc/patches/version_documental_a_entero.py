# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""La versión documental pasa de texto a número entero.

UPeU decidió el 2026-08-24 numerar sus versiones con enteros —1, 2, 3—: una
versión solo existe cuando se aprueba, así que no hay medias versiones. Ninguna
norma ISO prescribe el formato (ni 9001 ni 21001 hablan de numeración, solo
exigen identificar y controlar las versiones); es convención de la casa.

**Por qué hace falta un patch y no basta con cambiar el `.json`.** PostgreSQL no
convierte `varchar` a `integer` por su cuenta: el `ALTER TABLE` del sync falla con
«column cannot be cast automatically... You might need to specify USING
version::integer». Frappe abandona esa columna y deja el DocType como estaba, sin
romper el resto del migrate — así que el cambio parece aplicado y no lo está.
Comprobado en producción ese mismo día: tras el deploy, la columna seguía siendo
`character varying` y el meta seguía diciendo `Data`.

Va en `pre_model_sync` porque tiene que ocurrir ANTES de que Frappe intente
sincronizar el DocType; si corriera después, ya habría fallado.

Los valores existentes se convierten quedándose con la parte entera: «1.0» y
«1.5» pasan a 1. Es lo correcto para este caso —una «1.5» nunca fue una versión
aprobada— y, en todo caso, hoy no hay ningún documento en el sistema.
"""

import frappe

TABLAS = (
	("tabDocumento Controlado", "version"),
	("tabCambio Documento", "version"),
)


def execute():
	for tabla, columna in TABLAS:
		if not frappe.db.table_exists(tabla.replace("tab", "", 1)):
			continue
		tipo = frappe.db.sql(
			"""select data_type from information_schema.columns
			   where table_name = %s and column_name = %s""",
			(tabla, columna),
		)
		if not tipo or tipo[0][0] == "integer":
			continue

		# `split_part` se queda con lo anterior al punto y `NULLIF` evita que una
		# cadena vacía reviente el cast. Lo que no sea un número se queda a 0, que
		# es visiblemente incorrecto y por tanto revisable — mejor que perderlo.
		frappe.db.sql(
			f"""
			alter table "{tabla}"
			alter column "{columna}" type integer
			using coalesce(
				nullif(regexp_replace(split_part(coalesce("{columna}", ''), '.', 1), '[^0-9]', '', 'g'), '')::integer,
				0
			)
			"""
		)
		print(f"  {tabla}.{columna}: varchar -> integer")
