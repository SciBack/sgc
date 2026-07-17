# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Suite de tests para el M06 — Programa Auditoria (programa anual).

El controlador (`programa_auditoria.py`) aplica validaciones INCREMENTALES por
etapa según el Select `estado` (Borrador -> Aprobado -> En ejecucion -> Cerrado):
a partir de "Aprobado" exige responsable y aprobado_por, y autocompleta la
fecha de aprobación. También autogenera el código PGA-{anio}-NNNN.

Programa Auditoria tiene Workflow ("Programa Auditoria SGC") -> se desactiva en
setUp para poder crear el programa directamente en el estado que cada test
necesita, dejando correr solo las validaciones del CONTROLADOR.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

ADMIN = "Administrator"


class IntegrationTestProgramaAuditoria(IntegrationTestCase):
    """Validaciones incrementales por etapa del M06 (Programa Auditoria)."""

    def setUp(self):
        factories.desactivar_workflow("Programa Auditoria")

    # -- helper -------------------------------------------------------------
    def _programa(self, **overrides):
        vals = {
            "doctype": "Programa Auditoria",
            "titulo": "Programa anual de auditorías M06",
            "estado": "Borrador",
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
        p = self._programa()
        self.assertTrue(p.codigo.startswith("PGA-"))
        self.assertEqual(p.name, p.codigo)

    def test_codigo_respeta_el_indicado(self):
        p = self._programa(codigo="TEST-PGA-99")
        self.assertEqual(p.name, "TEST-PGA-99")

    # ======================================================================
    # nivel >= 1 — Aprobado
    # ======================================================================
    def test_aprobado_sin_responsable_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._programa(estado="Aprobado", aprobado_por=ADMIN)

    def test_aprobado_sin_aprobado_por_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._programa(estado="Aprobado", responsable=ADMIN)

    def test_aprobado_completo_autocompleta_fecha(self):
        p = self._programa(estado="Aprobado", responsable=ADMIN, aprobado_por=ADMIN)
        self.assertEqual(p.estado, "Aprobado")
        self.assertEqual(str(p.fecha_aprobacion), nowdate())

    def test_borrador_minimo_ok(self):
        p = self._programa()
        self.assertEqual(p.estado, "Borrador")
