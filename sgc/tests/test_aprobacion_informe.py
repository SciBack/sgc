# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Revisión y aprobación del informe de auditoría (#37, ISO 19011 §6.5).

  Informe
    - enviar a revisión exige contenido y sella quién lo emitió
    - devolver exige observaciones
    - no aprueba quien lo emitió, quien lo creó ni nadie del equipo auditor
    - aprobar y distribuir los sella el sistema; distribuir exige destinatarios
    - lo aprobado no cambia: ni el contenido ni los contadores
  Lo que pide el pliego («aprobación antes de levantar los hallazgos»)
    - un hallazgo no se cierra sin el informe aprobado
    - la auditoría no se cierra sin el informe aprobado
  Workflow
    - aprobar es de la DPGC sin autoaprobación; recorrido completo con tres personas

Todo se deshace al final de cada test (rollback de `IntegrationTestCase`).
"""

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase

from sgc.tests import factories

INFORME = "Informe Auditoria"
EMISOR = "sgc-prueba-inf-emisor@example.com"
APROBADOR = "sgc-prueba-inf-aprobador@example.com"
DEL_EQUIPO = "sgc-prueba-inf-equipo@example.com"


def _usuario(correo, *roles):
    if frappe.db.exists("User", correo):
        return
    u = frappe.get_doc({"doctype": "User", "email": correo, "first_name": correo.split("@")[0],
                        "send_welcome_email": 0})
    for rol in ("System Manager", *roles):
        u.append("roles", {"role": rol})
    u.insert(ignore_permissions=True)


class _Base(IntegrationTestCase):
    def setUp(self):
        _usuario(EMISOR, "Auditor Interno")
        _usuario(APROBADOR, "DPGC")
        _usuario(DEL_EQUIPO, "DPGC", "Auditor Interno")
        factories.desactivar_workflow("Auditoria")
        aud = frappe.get_doc({
            "doctype": "Auditoria", "titulo": "Auditoría de prueba #37",
            "equipo": [{"usuario": DEL_EQUIPO, "rol": "Auditor lider", "independiente_del_area": 1}],
            "criterios": [{"tipo_criterio": "Clausula norma", "referencia": "ISO 9001 9.2"}],
        }).insert(ignore_permissions=True)
        self.auditoria = aud.name

    def tearDown(self):
        frappe.set_user("Administrator")

    def _como(self, usuario):
        frappe.set_user(usuario)
        self.addCleanup(frappe.set_user, "Administrator")

    def _informe(self, **overrides):
        vals = {"doctype": INFORME, "auditoria": self.auditoria,
                "conclusiones": "Dos no conformidades menores en el proceso de actas."}
        vals.update(overrides)
        return frappe.get_doc(vals).insert(ignore_permissions=True)


class IntegrationTestAprobacionInforme(_Base):
    def setUp(self):
        super().setUp()
        factories.desactivar_workflow(INFORME)

    def _mover(self, inf, estado, como=None, **campos):
        if como:
            self._como(como)
        inf.update(campos)
        inf.estado = estado
        inf.save(ignore_permissions=True)
        frappe.set_user("Administrator")
        return inf

    def _en_revision(self):
        return self._mover(self._informe(), "En revision", como=EMISOR)

    # -- emitir -------------------------------------------------------------------
    def test_nace_en_borrador(self):
        self.assertEqual(self._informe().estado, "Borrador")

    def test_enviar_a_revision_sin_contenido_se_rechaza(self):
        inf = self._informe(conclusiones="")
        with self.assertRaises(frappe.ValidationError):
            self._mover(inf, "En revision", como=EMISOR)

    def test_enviar_a_revision_sella_quien_lo_emite(self):
        inf = self._en_revision()
        self.assertEqual(inf.emitido_por, EMISOR)
        self.assertTrue(inf.fecha_emision)

    def test_devolver_sin_observaciones_se_rechaza(self):
        inf = self._en_revision()
        with self.assertRaises(frappe.ValidationError) as ctx:
            self._mover(inf, "Borrador", como=APROBADOR)
        self.assertIn("observaciones", str(ctx.exception))

    def test_devolver_con_observaciones(self):
        inf = self._mover(self._en_revision(), "Borrador", como=APROBADOR,
                          observaciones_revision="Falta la muestra revisada.")
        self.assertEqual(inf.estado, "Borrador")

    # -- aprobar ------------------------------------------------------------------
    def test_quien_lo_emitio_no_lo_aprueba(self):
        with self.assertRaises(frappe.ValidationError) as ctx:
            self._mover(self._en_revision(), "Aprobado", como=EMISOR)
        self.assertIn("independiente", str(ctx.exception))

    def test_alguien_del_equipo_auditor_no_lo_aprueba(self):
        with self.assertRaises(frappe.ValidationError):
            self._mover(self._en_revision(), "Aprobado", como=DEL_EQUIPO)

    def test_quien_lo_creo_no_lo_aprueba(self):
        """El owner (aquí Administrator) tampoco, aunque no lo enviara él."""
        with self.assertRaises(frappe.ValidationError):
            self._mover(self._en_revision(), "Aprobado", como="Administrator")

    def test_aprobar_sella_quien_y_cuando(self):
        inf = self._mover(self._en_revision(), "Aprobado", como=APROBADOR)
        self.assertEqual(inf.aprobado_por, APROBADOR)
        self.assertTrue(inf.fecha_aprobacion)

    # -- lo aprobado no cambia ---------------------------------------------------
    def _aprobado(self):
        return self._mover(self._en_revision(), "Aprobado", como=APROBADOR)

    def test_el_contenido_aprobado_no_se_modifica(self):
        inf = self._aprobado()
        inf.conclusiones = "Otra cosa."
        with self.assertRaises(frappe.ValidationError) as ctx:
            inf.save(ignore_permissions=True)
        self.assertIn("conclusiones", str(ctx.exception))

    def test_los_contadores_aprobados_no_cambian(self):
        inf = self._aprobado()
        antes = inf.n_nc_menores
        frappe.get_doc({"doctype": "Hallazgo Auditoria", "auditoria": self.auditoria,
                        "tipo": "No conformidad menor", "descripcion": "Hallazgo tardío"}
                       ).insert(ignore_permissions=True)
        inf.reload()
        inf.destinatarios = "Rectorado"
        inf.save(ignore_permissions=True)
        self.assertEqual(inf.n_nc_menores, antes)

    # -- distribuir ---------------------------------------------------------------
    def test_distribuir_sin_destinatarios_se_rechaza(self):
        with self.assertRaises(frappe.ValidationError):
            self._mover(self._aprobado(), "Distribuido", como=APROBADOR)

    def test_distribuir_sella_quien_y_cuando(self):
        inf = self._mover(self._aprobado(), "Distribuido", como=APROBADOR,
                          destinatarios="Rectorado; Dirección de Planificación")
        self.assertEqual(inf.distribuido_por, APROBADOR)
        self.assertTrue(inf.fecha_distribucion)


class IntegrationTestAprobacionAntesDeLevantar(_Base):
    """Lo que pide el pliego: el informe se aprueba antes de levantar los hallazgos."""

    def setUp(self):
        super().setUp()
        factories.desactivar_workflow(INFORME)
        factories.desactivar_workflow("Hallazgo Auditoria")

    def _hallazgo(self):
        return frappe.get_doc({"doctype": "Hallazgo Auditoria", "auditoria": self.auditoria,
                               "tipo": "Observacion", "descripcion": "Observación de prueba"}
                              ).insert(ignore_permissions=True)

    def test_un_hallazgo_no_se_levanta_sin_informe_aprobado(self):
        self._informe()
        h = self._hallazgo()
        h.estado = "Cerrado"
        with self.assertRaises(frappe.ValidationError) as ctx:
            h.save(ignore_permissions=True)
        self.assertIn("no está aprobado", str(ctx.exception))

    def test_con_el_informe_aprobado_el_hallazgo_se_levanta(self):
        inf = self._informe()
        frappe.db.set_value(INFORME, inf.name, "estado", "Aprobado", update_modified=False)
        h = self._hallazgo()
        h.estado = "Cerrado"
        h.save(ignore_permissions=True)
        self.assertEqual(h.estado, "Cerrado")

    def test_la_auditoria_no_se_cierra_sin_informe_aprobado(self):
        inf = self._informe()
        frappe.db.set_value("Auditoria", self.auditoria, "estado", "Informe emitido",
                            update_modified=False)
        aud = frappe.get_doc("Auditoria", self.auditoria)
        self.assertEqual(aud.informe, inf.name)
        aud.estado = "Cerrada"
        with self.assertRaises(frappe.ValidationError) as ctx:
            aud.save(ignore_permissions=True)
        self.assertIn("no está aprobado", str(ctx.exception))

        frappe.db.set_value(INFORME, inf.name, "estado", "Aprobado", update_modified=False)
        aud.reload()
        aud.estado = "Cerrada"
        aud.save(ignore_permissions=True)
        self.assertEqual(aud.estado, "Cerrada")


class IntegrationTestInformeWorkflow(_Base):
    def _workflow(self):
        return frappe.db.get_value("Workflow", {"document_type": INFORME, "is_active": 1}, "name")

    def test_aprobar_es_de_la_dpgc_sin_autoaprobacion(self):
        wf = self._workflow()
        self.assertIsNotNone(wf, "Informe Auditoria debe tener workflow (f24)")
        aprobar = frappe.get_all("Workflow Transition", filters={"parent": wf, "action": "Aprobar"},
                                 fields=["allowed", "allow_self_approval"])
        self.assertTrue(aprobar)
        for t in aprobar:
            self.assertEqual(t.allowed, "DPGC")
            self.assertFalse(t.allow_self_approval)

    def test_recorrido_completo_por_el_motor(self):
        if not self._workflow():
            self.skipTest("workflow f24 no aplicado en este sitio")
        inf = self._informe()

        self._como(EMISOR)
        inf = apply_workflow(frappe.get_doc(INFORME, inf.name), "Enviar a revision")
        self.assertEqual((inf.estado, inf.emitido_por), ("En revision", EMISOR))

        self._como(APROBADOR)
        inf = apply_workflow(frappe.get_doc(INFORME, inf.name), "Aprobar")
        self.assertEqual((inf.estado, inf.aprobado_por), ("Aprobado", APROBADOR))

        frappe.db.set_value(INFORME, inf.name, "destinatarios", "Rectorado", update_modified=False)
        inf = apply_workflow(frappe.get_doc(INFORME, inf.name), "Distribuir")
        self.assertEqual((inf.estado, inf.distribuido_por), ("Distribuido", APROBADOR))
