# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Suite de tests para el M06 — Informe Auditoria (consolidación de hallazgos).

Verifica:
  - Autogeneración del código IAU-{anio}-NNNN (autoname field:codigo).
  - `validate` recuenta los hallazgos de la auditoría por tipo y fija los
    contadores (n_nc_mayores / n_nc_menores / n_observaciones / n_om).
  - Autocompleta fecha_emision y emitido_por.
  - `on_update` enlaza de vuelta la auditoría (Auditoria.informe).

Auditoria tiene Workflow ("Auditoria SGC") -> se desactiva en setUp.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestInformeAuditoria(IntegrationTestCase):
    """Consolidación de hallazgos y enlace de vuelta del M06 (Informe Auditoria)."""

    def setUp(self):
        factories.desactivar_workflow("Auditoria")
        self.auditoria = self._auditoria()

    # -- helpers ------------------------------------------------------------
    def _auditoria(self):
        doc = frappe.get_doc({
            "doctype": "Auditoria",
            "titulo": "M06 auditoría para informe",
            "tipo": "Interna",
            "estado": "Planificada",
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _hallazgo(self, tipo):
        doc = frappe.get_doc({
            "doctype": "Hallazgo Auditoria",
            "auditoria": self.auditoria.name,
            "tipo": tipo,
            "descripcion": "Hallazgo de prueba.",
            "estado": "Abierto",
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _informe(self):
        doc = frappe.get_doc({
            "doctype": "Informe Auditoria",
            "auditoria": self.auditoria.name,
            "conclusiones": "Conclusiones de prueba.",
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    # ======================================================================
    # Autogeneración + autocompletado
    # ======================================================================
    def test_codigo_y_autocompletado(self):
        inf = self._informe()
        self.assertTrue(inf.codigo.startswith("IAU-"))
        self.assertEqual(str(inf.fecha_emision), nowdate())
        self.assertEqual(inf.emitido_por, frappe.session.user)

    # ======================================================================
    # Consolidación de hallazgos
    # ======================================================================
    def test_consolida_hallazgos_por_tipo(self):
        self._hallazgo("No conformidad mayor")
        self._hallazgo("No conformidad menor")
        self._hallazgo("No conformidad menor")
        self._hallazgo("Observacion")
        self._hallazgo("Oportunidad de mejora")
        # Estos NO cuentan en ningún contador:
        self._hallazgo("Conformidad")
        self._hallazgo("Fortaleza")

        inf = self._informe()
        self.assertEqual(inf.n_nc_mayores, 1)
        self.assertEqual(inf.n_nc_menores, 2)
        self.assertEqual(inf.n_observaciones, 1)
        self.assertEqual(inf.n_om, 1)

    def test_sin_hallazgos_contadores_en_cero(self):
        inf = self._informe()
        self.assertEqual(inf.n_nc_mayores, 0)
        self.assertEqual(inf.n_nc_menores, 0)
        self.assertEqual(inf.n_observaciones, 0)
        self.assertEqual(inf.n_om, 0)

    # ======================================================================
    # Enlace de vuelta a la auditoría
    # ======================================================================
    def test_enlaza_de_vuelta_la_auditoria(self):
        inf = self._informe()
        vinculo = frappe.db.get_value("Auditoria", self.auditoria.name, "informe")
        self.assertEqual(vinculo, inf.name)
