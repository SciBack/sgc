# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M08 — Hallazgo de autoevaluación.

Fase 2 (2026-07-19): el escalado Hallazgo -> No Conformidad YA está implementado
y probado en `sgc/capa.py::escalar_a_no_conformidad()` (parte de la cadena
completa Valoracion Criterio -> Hallazgo -> No Conformidad -> Plan Mejora,
usada por `setup/f2_e2e_test.py`). Un hallazgo previo de este mismo plan de
acción decía "la rama de autoevaluación del CAPA no está implementada" —
estaba desactualizado: SÍ lo está, solo que como funciones de módulo, no como
método del documento (a diferencia de `HallazgoAuditoria.escalar_a_no_conformidad`).

Lo que faltaba de verdad: `capa.py` no tiene ningún `@frappe.whitelist()` — nada
en la UI/API puede dispararlo, solo scripts. Este controlador agrega SOLO un
wrapper delgado, reutilizando la lógica ya probada (no la duplica).
"""
import frappe
from frappe.model.document import Document

from sgc.capa import escalar_a_no_conformidad as _escalar


class Hallazgo(Document):
    @frappe.whitelist()
    def escalar_a_no_conformidad(self):
        """Wrapper whitelisted sobre `sgc.capa.escalar_a_no_conformidad` — expone
        a la UI/API la lógica ya implementada y probada en `capa.py`. Devuelve
        el name de la No Conformidad (idempotente, ver `capa.py`)."""
        return _escalar(self.name).name
