# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Mejora continua y auditoría: los tres requisitos que estaban a medias.

  M1  — «Potencial no conformidad» como tipo de no conformidad
  M8  — el plan aprobado se difunde por correo a quien tiene que ejecutarlo
  A13 — nº de NC, de acciones de mejora y de incidencias: tarjetas del cuadro
        de mando y recuento de acciones en el informe de auditoría

El envío real se sustituye por un doble (`_make`): el CI no tiene cuenta de correo.
Todo se deshace al final de la clase (rollback de IntegrationTestCase).
"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sgc import dashboards
from sgc.setup import f4_workflow_mejora as f4
from sgc.setup import f21_dashboards as f21
from sgc.tests import factories

MAKE = "frappe.core.doctype.communication.email._make"
DOMINIO = "sgc-prueba-mejora.example.com"
RESP_PLAN = f"plan@{DOMINIO}"
RESP_A = f"accion-a@{DOMINIO}"
RESP_B = f"accion-b@{DOMINIO}"


def _usuario(correo):
    if not frappe.db.exists("User", correo):
        u = frappe.get_doc({"doctype": "User", "email": correo, "first_name": correo.split("@")[0],
                            "send_welcome_email": 0})
        u.append("roles", {"role": "Responsable de Calidad de Programa"})
        u.insert(ignore_permissions=True)


def _correo(modo, lista=""):
    cfg = frappe.get_single("Configuracion Correo")
    cfg.modo = modo
    cfg.lista_blanca = lista
    cfg.save(ignore_permissions=True)


class _Base(IntegrationTestCase):
    def setUp(self):
        for u in (RESP_PLAN, RESP_A, RESP_B):
            _usuario(u)

    def _sin_workflow(self, doctype, nombre):
        factories.desactivar_workflow(doctype)
        self.addCleanup(frappe.clear_cache, doctype=doctype)
        self.addCleanup(frappe.db.set_value, "Workflow", nombre, "is_active", 1)

    def _plan(self, estado="Borrador", **kw):
        return frappe.get_doc({"doctype": "Plan Mejora", "codigo": f"TEST-PMP-{frappe.generate_hash(length=8)}",
                               "titulo": "Plan de prueba", "estado": estado, **kw}).insert(ignore_permissions=True)

    def _accion(self, plan, responsable, **kw):
        return frappe.get_doc({"doctype": "Accion Mejora", "codigo": f"TEST-AMP-{frappe.generate_hash(length=8)}",
                               "plan_mejora": plan.name, "descripcion": "Revisar el procedimiento",
                               "tipo": "Correctiva", "estado": "Planificada", "responsable": responsable,
                               **kw}).insert(ignore_permissions=True)


class IntegrationTestPotencialNoConformidad(_Base):
    def test_es_un_tipo_de_no_conformidad(self):
        opciones = frappe.get_meta("No Conformidad").get_field("tipo").options.split("\n")
        self.assertIn("Potencial no conformidad", opciones)
        nc = frappe.get_doc({"doctype": "No Conformidad", "titulo": "Riesgo de incumplir el plazo de actas",
                             "tipo": "Potencial no conformidad", "estado": "Abierta"}).insert(ignore_permissions=True)
        self.assertEqual(nc.tipo, "Potencial no conformidad")
        # No es una NC mayor: el análisis de causa no se impone solo.
        self.assertFalse(nc.requiere_analisis_causa)


class IntegrationTestDifusionDelPlan(_Base):
    def setUp(self):
        super().setUp()
        self._sin_workflow("Plan Mejora", f4.WF_PLAN["name"])

    def _aprobar(self, plan):
        plan.estado = "En ejecucion"
        plan.save(ignore_permissions=True)
        return plan

    def test_al_aprobarse_llega_al_responsable_del_plan_y_de_cada_accion(self):
        _correo("Real")
        plan = self._plan(responsable=RESP_PLAN)
        self._accion(plan, RESP_A)
        self._accion(plan, RESP_B)
        with patch(MAKE) as make:
            self._aprobar(plan)
        make.assert_called_once()
        args = make.call_args.kwargs
        self.assertEqual(set(args["recipients"]), {RESP_PLAN, RESP_A, RESP_B})
        self.assertEqual((args["doctype"], args["name"]), ("Plan Mejora", plan.name))
        self.assertIn("Revisar el procedimiento", args["content"])

    def test_solo_en_la_transicion(self):
        _correo("Real")
        with patch(MAKE) as make:
            plan = self._plan(estado="En ejecucion", responsable=RESP_PLAN)
            self._accion(plan, RESP_A)
            plan.titulo = "Otro título"
            plan.save(ignore_permissions=True)
        make.assert_not_called()

    def test_pasa_por_la_lista_blanca(self):
        _correo("Real", RESP_A)
        plan = self._plan(responsable=RESP_PLAN)
        self._accion(plan, RESP_A)
        with patch(MAKE) as make:
            self._aprobar(plan)
        self.assertEqual(make.call_args.kwargs["recipients"], [RESP_A])


class IntegrationTestIndicadoresA13(_Base):
    def test_tarjetas_de_acciones_e_incidencias(self):
        # No se llama a f21.run(): comitea y dejaría persistidos los datos de la clase.
        # Las tarjetas las crea el despliegue (after_migrate).
        declaradas = {c["label"]: c for c in f21.NUMBER_CARDS}
        for etiqueta, metodo in (("SGC - Acciones de mejora abiertas", "sgc.dashboards.acciones_abiertas"),
                                 ("SGC - Incidencias abiertas", "sgc.dashboards.incidencias_abiertas")):
            self.assertEqual(declaradas[etiqueta]["method"], metodo)

    def test_incidencias_suma_salidas_y_eventos_abiertos(self):
        antes = dashboards.incidencias_abiertas()
        proceso = factories.crear_proceso(prefijo="A13").name
        frappe.get_doc({"doctype": "Salida No Conforme", "titulo": "Actas con error", "origen": "Interno",
                        "proceso": proceso, "descripcion": "x", "requisito_incumplido": "Reglamento"}).insert(ignore_permissions=True)
        frappe.get_doc({"doctype": "Evento Riesgo", "titulo": "Caída del servicio",
                        "fecha_evento": frappe.utils.nowdate(), "descripcion": "x"}).insert(ignore_permissions=True)
        self.assertEqual(dashboards.incidencias_abiertas(), antes + 2)

    def test_acciones_abiertas_cuenta_las_no_verificadas(self):
        antes = dashboards.acciones_abiertas()
        plan = self._plan(responsable=RESP_PLAN)
        self._accion(plan, RESP_A)
        self.assertEqual(dashboards.acciones_abiertas(), antes + 1)

    def test_el_informe_de_auditoria_cuenta_sus_acciones_de_mejora(self):
        self._sin_workflow("Auditoria", "Auditoria SGC")
        auditoria = frappe.get_doc({"doctype": "Auditoria", "titulo": "A13 auditoría", "tipo": "Interna",
                                    "estado": "Planificada"}).insert(ignore_permissions=True)
        nc = frappe.get_doc({"doctype": "No Conformidad", "titulo": "NC de la auditoría",
                             "tipo": "No conformidad menor", "estado": "Abierta"}).insert(ignore_permissions=True)
        frappe.get_doc({"doctype": "Hallazgo Auditoria", "auditoria": auditoria.name,
                        "tipo": "No conformidad menor", "descripcion": "x", "estado": "Abierto",
                        "no_conformidad": nc.name}).insert(ignore_permissions=True)
        plan = self._plan(responsable=RESP_PLAN)
        self._accion(plan, RESP_A, no_conformidad=nc.name)
        self._accion(plan, RESP_B)  # no sale de esta auditoría
        informe = frappe.get_doc({"doctype": "Informe Auditoria", "auditoria": auditoria.name,
                                  "conclusiones": "x"}).insert(ignore_permissions=True)
        self.assertEqual(informe.n_nc_menores, 1)
        self.assertEqual(informe.n_acciones_mejora, 1)
