# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Riesgo — inventario GRC.

Fase 2 (2026-07-19, hallazgo): la cadena ISO 9001 §6.1/§10.2 (un riesgo que se
materializa debe alimentar el CAPA) estaba rota — `Riesgo` no tenía ningún camino
a `No Conformidad`. El esquema YA anticipaba esto (`No Conformidad.origen_tipo`
incluye "Riesgo materializado" desde el diseño original), pero nadie implementó
el método que lo dispara. Mismo patrón que
`sgc/sgc_auditoria/doctype/hallazgo_auditoria/hallazgo_auditoria.py::escalar_a_no_conformidad`
— reutiliza el origen polimórfico existente, no crea un mecanismo nuevo.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class Riesgo(Document):
    @frappe.whitelist()
    def escalar_a_no_conformidad(self):
        """Escala este riesgo (ya materializado) a una `No Conformidad`.

        Solo tiene sentido si `estado == "Materializado"` — un riesgo que no se
        materializó no es una no conformidad, es gestión preventiva normal.
        Idempotente: si ya hay una NC ligada (buscada por origen), devuelve esa.
        """
        if self.estado != "Materializado":
            frappe.throw(
                _("Solo un riesgo en estado «Materializado» puede escalar a una "
                  "No Conformidad. Estado actual: «{0}».").format(self.estado or _("(sin estado)"))
            )

        existente = frappe.db.get_value(
            "No Conformidad",
            {"origen_doctype": "Riesgo", "origen_id": self.name},
            "name",
        )
        if existente:
            return existente

        nc = frappe.get_doc({
            "doctype": "No Conformidad",
            "titulo": _("NC desde riesgo materializado {0}").format(self.name),
            "origen_doctype": "Riesgo",
            "origen_id": self.name,
            "origen_tipo": "Riesgo materializado",
            "tipo": "No conformidad mayor",
            "descripcion": self.descripcion or "",
            "unidad_organica": self.unidad_organica,
            "proceso": self.proceso,
            "criterio": self.elemento_marco,
            "estado": "Abierta",
            "requiere_analisis_causa": 1,
            "fecha_deteccion": nowdate(),
        }).insert(ignore_permissions=True)

        return nc.name
