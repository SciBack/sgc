"""El estado del plazo de los registros que ya existían (1.7.16).

Los registros nuevos lo calculan al guardarse (`sgc/plazos.py`). Los anteriores no se
vuelven a guardar solos: esto lo hace una vez, sin pasar por `save` para no disparar
validaciones ni avisos de estados que ya ocurrieron.

La fecha de cierre de un registro ya cerrado no se registraba (salvo en el Plan de
mejora, que la conserva): se toma la de su última modificación, que en un registro
cerrado es normalmente su cierre. Es la mejor aproximación disponible.
"""

import frappe
from frappe.utils import getdate

from sgc import plazos


def execute():
	for doctype, cierres in plazos.CIERRES.items():
		filas = frappe.get_all(doctype, fields=["name", "estado", "fecha_compromiso", "fecha_cierre", "modified"])
		for fila in filas:
			fecha_cierre = (fila.fecha_cierre or getdate(fila.modified)) if fila.estado in cierres else None
			estado, dias = plazos.calcular(fila.fecha_compromiso, fecha_cierre)
			frappe.db.set_value(
				doctype,
				fila.name,
				{"fecha_cierre": fecha_cierre, "estado_plazo": estado, "dias_retraso": dias},
				update_modified=False,
			)
		if filas:
			print(f"{doctype}: estado del plazo en {len(filas)} registro(s)")
