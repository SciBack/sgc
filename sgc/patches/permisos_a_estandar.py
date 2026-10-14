"""Los permisos del SGC pasan a ser los estándar de cada DocType (1.2.0).

Hasta la 1.1.0, `f3b_rbac` escribía la matriz como Custom DocPerm en cada `migrate`. Desde la
1.2.0 la matriz va en los permisos estándar del propio DocType (su JSON). Frappe aplica los
Custom DocPerm si un DocType tiene alguno, así que, mientras sigan ahí, los estándar no cuentan.

Aquí se quitan los Custom DocPerm de un DocType del SGC SOLO si dicen lo mismo que los
estándar: el permiso efectivo no cambia, pero desde ahora manda el estándar y una actualización
puede corregirlo. Si una institución los cambió a mano (Role Permission Manager), no coinciden y
se dejan como están: es su decisión.

Se comparan sin las banderas que no tienen efecto en ese DocType (submit/cancel/amend en uno
que no se envía, import en uno que no se importa), que la validación estándar no admite.
"""

import frappe

from sgc import estandar

_BANDERAS = ("select", "read", "write", "create", "delete", "submit", "cancel", "amend", "report",
			 "export", "import", "share", "print", "email", "mask", "impersonate")


def _normalizar(filas, enviable, importable):
	salida = set()
	for f in filas:
		b = {c: int(f.get(c) or 0) for c in _BANDERAS}
		if not enviable:
			b.update(submit=0, cancel=0, amend=0)
		if not importable:
			b["import"] = 0
		if b["cancel"] and not b["submit"]:
			b["cancel"] = 0
		salida.add((f.get("role"), int(f.get("permlevel") or 0), int(f.get("if_owner") or 0), tuple(sorted(b.items()))))
	return salida


def execute():
	for dt in estandar.permisos():
		if not frappe.db.exists("DocType", dt):
			continue
		custom = frappe.get_all("Custom DocPerm", filters={"parent": dt}, fields=["*"])
		if not custom:
			continue
		meta = frappe.db.get_value("DocType", dt, ["is_submittable", "allow_import"], as_dict=True)
		estandar_dt = frappe.get_all("DocPerm", filters={"parent": dt, "parenttype": "DocType"}, fields=["*"])
		if _normalizar(custom, meta.is_submittable, meta.allow_import) == _normalizar(
			estandar_dt, meta.is_submittable, meta.allow_import
		):
			frappe.db.delete("Custom DocPerm", {"parent": dt})
		else:
			print(f"permisos_a_estandar: {dt} tiene permisos personalizados distintos; se conservan")
	frappe.clear_cache()
