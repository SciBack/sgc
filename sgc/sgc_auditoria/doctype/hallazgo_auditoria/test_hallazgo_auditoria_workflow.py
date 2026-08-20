# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""El hallazgo de auditoría no lo cierra quien lo levantó, ni escala en falso.

Era el único documento de la cadena de auditoría con su ciclo de vida en un
Select suelto. Recorriendo el flujo en producción (20-ago) se comprobó lo que
eso permitía: el mismo auditor que abría el hallazgo lo cerraba sin que nadie
verificara, y «Escalado a NC» podía marcarse con el vínculo vacío —declarando un
enlace M05↔M06 que no existía—.
"""
import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase


class IntegrationTestHallazgoAuditoriaWorkflow(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        a = frappe.get_doc({"doctype": "Auditoria", "titulo": "Auditoría de prueba WF"})
        a.flags.ignore_permissions = True
        a.insert(ignore_permissions=True)
        self.auditoria = a.name

    def _hallazgo(self, **kw):
        vals = {"doctype": "Hallazgo Auditoria", "auditoria": self.auditoria,
                "descripcion": "Hallazgo de prueba", "tipo": "No conformidad menor"}
        vals.update(kw)
        doc = frappe.get_doc(vals)
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def test_escalado_a_nc_exige_la_no_conformidad(self):
        """Declarar el escalamiento sin la NC deja el enlace M05↔M06 en falso."""
        doc = self._hallazgo()

        doc.estado = "Escalado a NC"
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc.save(ignore_permissions=True)

        self.assertIn("no conformidad", str(ctx.exception).lower())

    def test_escalar_de_verdad_crea_la_nc_y_mueve_el_estado(self):
        """La acción real sí escala: crea la NC, la vincula y transiciona."""
        doc = self._hallazgo()

        nc = doc.escalar_a_no_conformidad()

        self.assertTrue(frappe.db.exists("No Conformidad", nc))
        doc.reload()
        self.assertEqual(doc.no_conformidad, nc)
        self.assertEqual(doc.estado, "Escalado a NC")
        self.assertEqual(doc.genera_nc, 1)

    def test_el_workflow_esta_activo_y_cerrar_es_de_la_dpgc(self):
        """El cierre no es una acción disponible para el auditor que lo abrió."""
        wf = frappe.db.get_value("Workflow", {"document_type": "Hallazgo Auditoria"},
                                 ["name", "is_active"], as_dict=True)
        self.assertIsNotNone(wf, "Hallazgo Auditoria debe tener workflow (f16)")
        self.assertEqual(wf.is_active, 1)

        cerrar = frappe.get_all(
            "Workflow Transition",
            filters={"parent": wf.name, "action": "Cerrar"},
            fields=["allowed", "allow_self_approval"],
        )
        self.assertTrue(cerrar, "debe existir la transición Cerrar")
        for t in cerrar:
            self.assertEqual(t.allowed, "DPGC")
            self.assertFalse(t.allow_self_approval,
                             "quien levanta el hallazgo no puede cerrarlo")

    def test_saltar_a_cerrado_con_un_save_ya_no_funciona(self):
        """Con el workflow activo, el motor bloquea el atajo por save()."""
        doc = self._hallazgo()

        doc.estado = "Cerrado"
        with self.assertRaises(Exception):
            doc.save(ignore_permissions=True)
