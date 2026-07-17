# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Suite de tests para el M06 — Hallazgo Auditoria (escalamiento a M05).

Verifica:
  - Autogeneración del código HAU-{anio}-NNNN (autoname field:codigo).
  - `escalar_a_no_conformidad`: crea la No Conformidad (origen Auditoria), marca
    el hallazgo (no_conformidad, genera_nc=1, estado "Escalado a NC"), es
    idempotente y rechaza tipos que no constituyen no conformidad (Conformidad).

La NC tiene Workflow ("No Conformidad SGC") -> se desactiva en setUp para poder
insertarla desde el escalamiento sin WorkflowPermissionError.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

ADMIN = "Administrator"


class IntegrationTestHallazgoAuditoria(IntegrationTestCase):
    """Escalamiento Hallazgo Auditoria -> No Conformidad (puente §2)."""

    def setUp(self):
        factories.desactivar_workflow("Auditoria")
        factories.desactivar_workflow("No Conformidad")
        self.auditoria = self._auditoria()

    # -- helpers ------------------------------------------------------------
    def _auditoria(self):
        doc = frappe.get_doc({
            "doctype": "Auditoria",
            "titulo": "M06 auditoría para hallazgos",
            "tipo": "Interna",
            "estado": "Planificada",
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _hallazgo(self, tipo="No conformidad menor", **overrides):
        vals = {
            "doctype": "Hallazgo Auditoria",
            "auditoria": self.auditoria.name,
            "tipo": tipo,
            "descripcion": "Evidencia objetiva del hallazgo.",
            "criterio_incumplido": "ISO 9001 7.5.3",
            "estado": "Abierto",
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    # ======================================================================
    # Autogeneración de código
    # ======================================================================
    def test_codigo_autogenerado(self):
        h = self._hallazgo()
        self.assertTrue(h.codigo.startswith("HAU-"))
        self.assertEqual(h.name, h.codigo)

    # ======================================================================
    # Escalamiento a No Conformidad
    # ======================================================================
    def test_escala_a_no_conformidad(self):
        h = self._hallazgo(tipo="No conformidad mayor")
        nc_name = h.escalar_a_no_conformidad()

        self.assertTrue(nc_name)
        nc = frappe.get_doc("No Conformidad", nc_name)
        self.assertEqual(nc.origen_doctype, "Auditoria")
        self.assertEqual(nc.origen_id, self.auditoria.name)
        self.assertEqual(nc.origen_tipo, "Auditoria")
        self.assertEqual(nc.tipo, "No conformidad mayor")
        self.assertEqual(nc.requisito_incumplido, "ISO 9001 7.5.3")

        # el hallazgo queda marcado como escalado
        h.reload()
        self.assertEqual(h.no_conformidad, nc_name)
        self.assertEqual(h.genera_nc, 1)
        self.assertEqual(h.estado, "Escalado a NC")

    def test_escala_es_idempotente(self):
        h = self._hallazgo()
        primero = h.escalar_a_no_conformidad()
        segundo = h.escalar_a_no_conformidad()
        self.assertEqual(primero, segundo)

    def test_conformidad_no_escala(self):
        h = self._hallazgo(tipo="Conformidad")
        with self.assertRaises(frappe.ValidationError):
            h.escalar_a_no_conformidad()

    def test_no_conformidad_ligada_marca_estado_en_validate(self):
        # Si se liga una NC manualmente, validate() sincroniza genera_nc y estado.
        nc = frappe.get_doc({
            "doctype": "No Conformidad",
            "titulo": "NC manual de prueba",
            "tipo": "No conformidad menor",
            "estado": "Abierta",
        })
        nc.flags.ignore_permissions = True
        nc.insert(ignore_permissions=True)

        h = self._hallazgo(no_conformidad=nc.name)
        self.assertEqual(h.genera_nc, 1)
        self.assertEqual(h.estado, "Escalado a NC")
