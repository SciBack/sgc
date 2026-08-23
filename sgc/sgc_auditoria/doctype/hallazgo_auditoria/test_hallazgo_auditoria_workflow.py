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

    def _hallazgo_de_otro(self, **kw):
        """Igual, pero levantado por OTRA persona.

        «Cerrar» tiene `allow_self_approval=0` a propósito —quien levanta el
        hallazgo no lo cierra—, así que un hallazgo cuyo autor es quien corre el
        test no se puede cerrar por el motor, y el guard que se quiere probar ni
        siquiera llega a ejecutarse.
        """
        doc = self._hallazgo(**kw)
        frappe.db.set_value("Hallazgo Auditoria", doc.name, "owner", "Guest",
                            update_modified=False)
        return frappe.get_doc("Hallazgo Auditoria", doc.name)

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

    def test_el_auditor_no_puede_cerrar_por_el_motor(self):
        """La transición de cierre no está disponible para el Auditor Interno.

        Ojo con el alcance de lo que garantiza un workflow: Frappe NO impide
        reasignar `estado` con un `save()` a secas —eso vale para los 15
        workflows del sistema, no solo para este—; lo que impide es ejecutar la
        transición sin el rol. La regla «no se edita el estado directamente para
        saltar el workflow» está documentada en `docs-site/.../conceptos.md`
        como regla de uso, y el control efectivo son los permisos de campo y las
        transiciones.
        """
        from frappe.model.workflow import get_transitions

        doc = self._hallazgo()
        acciones_dpgc = {t["action"] for t in get_transitions(doc)}
        self.assertIn("Cerrar", acciones_dpgc,
                      "Administrator/DPGC sí ve la acción de cierre")

        transiciones = frappe.get_all(
            "Workflow Transition",
            filters={"parent": "Hallazgo Auditoria SGC", "action": "Cerrar"},
            fields=["allowed"],
        )
        self.assertTrue(transiciones)
        self.assertNotIn("Auditor Interno", {t.allowed for t in transiciones},
                         "el auditor que levanta el hallazgo no cierra")

    # ------------------------------------------------------------------
    # Cierre y reapertura (recorrido 08, 2026-08-23)
    # ------------------------------------------------------------------
    def test_una_no_conformidad_no_se_cierra_sin_escalar(self):
        """ISO 9001 §10.2.1: la reacción vive en la No Conformidad, no en el aire.

        Se cerraba con `genera_nc=0` y sin NC vinculada: el sistema quedaba
        afirmando que hubo una no conformidad mayor y que no se hizo nada.
        """
        for tipo in ("No conformidad mayor", "No conformidad menor"):
            doc = self._hallazgo_de_otro(tipo=tipo)

            with self.assertRaises(frappe.ValidationError, msg=tipo) as ctx:
                apply_workflow(doc, "Cerrar")

            self.assertIn("acción correctiva", str(ctx.exception))

    def test_una_observacion_si_se_cierra_sin_escalar(self):
        """Escalar una observación es opción, no obligación."""
        for tipo in ("Observacion", "Oportunidad de mejora", "Conformidad", "Fortaleza"):
            doc = self._hallazgo_de_otro(tipo=tipo)

            apply_workflow(doc, "Cerrar")

            self.assertEqual(doc.estado, "Cerrado", tipo)

    def test_una_no_conformidad_escalada_si_se_cierra(self):
        """El camino normal tiene que llegar: escala, y entonces cierra."""
        doc = self._hallazgo_de_otro(tipo="No conformidad mayor")
        doc.escalar_a_no_conformidad()

        doc = frappe.get_doc("Hallazgo Auditoria", doc.name)
        apply_workflow(doc, "Cerrar")

        self.assertEqual(doc.estado, "Cerrado")

    def test_un_hallazgo_escalado_se_reabre_a_escalado(self):
        """Volver a «Abierto» diría que nunca escaló, con la NC ahí delante.

        El caso que el propio comentario del workflow describe —«el cierre fue
        prematuro, la NC sigue abierta»— era justo el que NO funcionaba: el
        controlador fuerza «Escalado a NC» mientras haya NC ligada, así que
        «Reabrir» chocaba contra el motor con un mensaje que no decía nada.
        """
        doc = self._hallazgo_de_otro(tipo="No conformidad mayor")
        nc = doc.escalar_a_no_conformidad()
        doc = frappe.get_doc("Hallazgo Auditoria", doc.name)
        apply_workflow(doc, "Cerrar")

        doc = frappe.get_doc("Hallazgo Auditoria", doc.name)
        apply_workflow(doc, "Reabrir escalado")

        self.assertEqual(doc.estado, "Escalado a NC")
        self.assertEqual(doc.no_conformidad, nc)

    def test_reabrir_un_escalado_por_la_puerta_equivocada_lo_explica(self):
        """El mensaje tiene que decir cuál es la acción suya."""
        doc = self._hallazgo_de_otro(tipo="No conformidad mayor")
        doc.escalar_a_no_conformidad()
        doc = frappe.get_doc("Hallazgo Auditoria", doc.name)
        apply_workflow(doc, "Cerrar")

        doc = frappe.get_doc("Hallazgo Auditoria", doc.name)
        with self.assertRaises(frappe.ValidationError) as ctx:
            apply_workflow(doc, "Reabrir")

        self.assertIn("Reabrir escalado", str(ctx.exception))

    def test_un_hallazgo_sin_escalar_se_reabre_a_abierto(self):
        """El que nunca escaló sí vuelve a «Abierto»: es donde estaba."""
        doc = self._hallazgo_de_otro(tipo="Observacion")
        apply_workflow(doc, "Cerrar")

        doc = frappe.get_doc("Hallazgo Auditoria", doc.name)
        apply_workflow(doc, "Reabrir")

        self.assertEqual(doc.estado, "Abierto")

