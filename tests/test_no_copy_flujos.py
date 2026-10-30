"""Duplicar un documento no copia su estado del flujo ni las firmas que selló el sistema.

«Copiar» de Frappe (`frappe.model.copy_doc`) lleva todo campo que no sea `no_copy`. Sin esto, la
copia de un documento Publicado nacía «Publicada» y con el «Aprobado por» del original; al guardar,
el flujo la rechazaba con un error críptico. Con el estado vacío, Frappe pone el estado inicial
(`frappe/model/workflow.py`, `validate_workflow`). Se comprueba sin Frappe, leyendo los JSON.
"""

import json
import re
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "sgc"
SELLO = re.compile(
	r"^(aprobad[oa]|cerrad[oa]|verificad[oa]|emitid[oa]|distribuid[oa]|implementad[oa]|evaluad[oa]"
	r"|autorizad[oa]|reportad[oa]|elaborad[oa]|revisad[oa]|cargad[oa])_por$"
)


def _doctypes():
	for fichero in APP.glob("*/doctype/*/*.json"):
		try:
			datos = json.loads(fichero.read_text(encoding="utf-8"))
		except ValueError:
			continue
		if datos.get("doctype") == "DocType":
			yield datos


class TestNoCopyFlujos(unittest.TestCase):
	def setUp(self):
		flujos = json.loads((APP / "fixtures" / "workflow.json").read_text(encoding="utf-8"))
		self.estado = {f["document_type"]: f["workflow_state_field"] for f in flujos}
		self.doctypes = {d["name"]: d for d in _doctypes()}

	def test_el_estado_del_flujo_no_se_copia(self):
		faltan = [
			dt
			for dt, campo in self.estado.items()
			if not next(c for c in self.doctypes[dt]["fields"] if c["fieldname"] == campo).get("no_copy")
		]
		self.assertEqual(faltan, [])

	def test_las_firmas_del_sistema_no_se_copian(self):
		faltan = [
			f"{dt}.{c['fieldname']}"
			for dt in self.estado
			for c in self.doctypes[dt]["fields"]
			if SELLO.match(c["fieldname"]) and not c.get("no_copy")
		]
		self.assertEqual(faltan, [])


if __name__ == "__main__":
	unittest.main()
