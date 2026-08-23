# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Cumplimiento CBC — fila de la Table `condiciones` de `Informe Cumplimiento` (M01).

Una fila = una de las condiciones básicas de calidad (CBC) del Modelo de
Licenciamiento Institucional de la Sunedu (RCD 006-2015-SUNEDU/CD), con su juicio
cumple / cumple parcial / no cumple y su sustento.

`istable:1`: Frappe NUNCA invoca `validate()` de una fila de child table -- las
persiste con `Document.update_child_table()` -> `d.db_update()` directo, sin pasar
por `run_method("validate")`. Por eso el auto-sync de su picklist `evidencia`
(Evidencia Enlace) hacia `Trazabilidad` NO vive aquí (sería código muerto): vive
en el `validate()` del documento padre real, `InformeCumplimiento._sincronizar_trazabilidad`
(sgc/sgc_procesos/doctype/informe_cumplimiento/informe_cumplimiento.py), que sí
se ejecuta y ya tiene acceso a cada fila vía `self.condiciones`.
"""

from frappe.model.document import Document


class CumplimientoCBC(Document):
	pass
