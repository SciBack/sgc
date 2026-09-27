# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Reporte de eventos de riesgo por cualquier colaborador.

  Permisos (con usuarios SIN System Manager: lo que se prueba es la matriz)
    - un colaborador sin cargo en el SGC reporta, y ve solo lo que él reportó
    - un colaborador no toma decisiones sobre el reporte
  Controlador
    - quién reportó y cuándo lo sella el sistema; la fecha no puede ser futura
    - el proceso y la unidad se toman del riesgo si no se indican
    - quien reportó no decide; descartar exige motivo; lo decidido no se reescribe
  Confirmación
    - abre la no conformidad con trazabilidad, una sola vez, lista para el
      análisis de causas y el plan de acción
  Avisos
    - a la DPGC al reportarse, a quien reportó al decidirse
  Menús
    - el riesgo muestra sus eventos; el área de Riesgos tiene la pantalla

Todo se deshace al final de cada test (rollback de `IntegrationTestCase`).
"""

import frappe
from frappe.email.doctype.notification.notification import get_context
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc.setup import f3b_rbac, f18_workspace
from sgc.setup import f15_notificaciones_workflow as f15
from sgc.setup import f25_workflow_evento_riesgo as f25
from sgc.sgc_riesgos.doctype.evento_riesgo.evento_riesgo import ORIGEN_NC
from sgc.tests import factories

DOCTYPE = "Evento Riesgo"
DOMINIO = "sgc-prueba-evr.example.com"

COLAB = f"colaborador@{DOMINIO}"
COLAB_2 = f"colaborador2@{DOMINIO}"
DPGC = f"dpgc@{DOMINIO}"
DPGC_2 = f"dpgc2@{DOMINIO}"


def _usuario(correo, *roles):
    if frappe.db.exists("User", correo):
        return
    u = frappe.get_doc({"doctype": "User", "email": correo, "first_name": correo.split("@")[0],
                        "send_welcome_email": 0})
    for rol in roles:
        u.append("roles", {"role": rol})
    u.insert(ignore_permissions=True)


class _Base(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Lo que el despliegue deja puesto; los tres pasos son idempotentes.
        f3b_rbac._ensure_roles()
        f3b_rbac.aplicar_colaboradores()
        f25.run()
        f15.run()
        frappe.flags.in_patch = False
        frappe.clear_cache()

    def setUp(self):
        _usuario(COLAB, "Colaborador")
        _usuario(COLAB_2, "Colaborador")
        # DPGC decide con la matriz real, sin System Manager.
        _usuario(DPGC, "DPGC")
        _usuario(DPGC_2, "DPGC")
        self.proceso = factories.crear_proceso(prefijo="EVR").name

    def tearDown(self):
        frappe.set_user("Administrator")

    def _sin_workflow(self):
        """Desactiva el workflow para mover el estado a mano, y lo REACTIVA al
        terminar: el rollback de IntegrationTestCase es por clase, no por test, y
        el siguiente test de la clase se quedaría sin workflow."""
        factories.desactivar_workflow(DOCTYPE)
        self.addCleanup(frappe.clear_cache, doctype=DOCTYPE)
        self.addCleanup(frappe.db.set_value, "Workflow", f25.WF_EVENTO["name"], "is_active", 1)

    def _como(self, usuario):
        frappe.set_user(usuario)
        self.addCleanup(frappe.set_user, "Administrator")

    def _reportar(self, como=COLAB, **overrides):
        vals = {
            "doctype": DOCTYPE,
            "titulo": "Caída del sistema de matrícula",
            "fecha_evento": nowdate(),
            "proceso": self.proceso,
            "descripcion": "El sistema estuvo caído dos horas el primer día de matrícula.",
            "consecuencias": "Cola de estudiantes sin atender.",
            "acciones_inmediatas": "Se habilitó la atención presencial.",
        }
        vals.update(overrides)
        self._como(como)
        doc = frappe.get_doc(vals).insert()
        frappe.set_user("Administrator")
        return doc

    def _a(self, doc, accion, como):
        self._como(como)
        doc = apply_workflow(frappe.get_doc(DOCTYPE, doc.name), accion)
        frappe.set_user("Administrator")
        return doc

    def _en_evaluacion(self, **overrides):
        return self._a(self._reportar(**overrides), "Evaluar", DPGC)


class IntegrationTestEventoRiesgoPermisos(_Base):
    def test_el_colaborador_es_usuario_del_desk(self):
        self.assertEqual(frappe.db.get_value("Role", "Colaborador", "desk_access"), 1)
        self.assertEqual(frappe.db.get_value("User", COLAB, "user_type"), "System User")

    def test_un_colaborador_reporta_y_queda_sellado(self):
        doc = self._reportar()
        self.assertEqual(doc.estado, "Reportado")
        self.assertEqual(doc.reportado_por, COLAB)
        self.assertTrue(doc.fecha_reporte)

    def test_el_sello_no_se_teclea(self):
        doc = self._reportar(reportado_por=COLAB_2, evaluado_por=COLAB_2)
        self.assertEqual(doc.reportado_por, COLAB)
        self.assertFalse(doc.evaluado_por)

    def test_cada_colaborador_ve_solo_lo_suyo(self):
        mio = self._reportar(como=COLAB)
        ajeno = self._reportar(como=COLAB_2)
        self._como(COLAB)
        visibles = set(frappe.get_list(DOCTYPE, pluck="name"))
        self.assertIn(mio.name, visibles)
        self.assertNotIn(ajeno.name, visibles)
        self.assertFalse(frappe.has_permission(DOCTYPE, "read", ajeno.name))

    def test_la_dpgc_ve_todos(self):
        a = self._reportar(como=COLAB)
        b = self._reportar(como=COLAB_2)
        self._como(DPGC)
        visibles = set(frappe.get_list(DOCTYPE, pluck="name"))
        self.assertTrue({a.name, b.name} <= visibles)

    def test_elige_el_proceso_sin_poder_abrirlo(self):
        """Sin «select», el campo Proceso del reporte no le ofrecía nada."""
        self._como(COLAB)
        for catalogo in ("Proceso", "Unidad Organica"):
            with self.subTest(catalogo=catalogo):
                self.assertTrue(frappe.has_permission(catalogo, "select"))
                self.assertFalse(frappe.has_permission(catalogo, "read"))
        # El registro de riesgos no se abre a todos: el riesgo lo asigna Calidad.
        self.assertFalse(frappe.has_permission("Riesgo", "select"))

    def test_un_colaborador_no_evalua(self):
        doc = self._reportar()
        with self.assertRaises(frappe.ValidationError):
            self._a(doc, "Evaluar", COLAB)


class IntegrationTestEventoRiesgoControlador(_Base):
    def test_la_fecha_no_puede_ser_futura(self):
        with self.assertRaises(frappe.ValidationError):
            self._reportar(fecha_evento=add_days(nowdate(), 2))

    def test_toma_proceso_y_unidad_del_riesgo(self):
        riesgo = frappe.get_doc({
            "doctype": "Riesgo", "titulo": "Caída de servicios críticos",
            "descripcion": "prueba", "categoria": "Operacional", "proceso": self.proceso,
        }).insert(ignore_permissions=True)
        doc = self._reportar(proceso=None, riesgo=riesgo.name)
        self.assertEqual(doc.proceso, self.proceso)

    def test_descartar_exige_motivo_y_se_sella(self):
        doc = self._en_evaluacion()
        with self.assertRaises(frappe.ValidationError):
            self._a(doc, "Descartar", DPGC)
        frappe.db.set_value(DOCTYPE, doc.name, "motivo_descarte", "Es un duplicado de otro reporte.")
        doc = self._a(doc, "Descartar", DPGC)
        self.assertEqual(doc.estado, "Descartado")
        self.assertEqual(doc.evaluado_por, DPGC)
        self.assertTrue(doc.fecha_evaluacion)
        self.assertFalse(doc.no_conformidad)

    def test_quien_reporta_no_decide(self):
        doc = self._reportar(como=DPGC)
        doc = self._a(doc, "Evaluar", DPGC)  # tomarlo en evaluación no decide nada
        with self.assertRaises(frappe.ValidationError):
            self._a(doc, "Confirmar", DPGC)
        # Tampoco por la puerta de atrás: el controlador, no solo el motor.
        self._sin_workflow()
        d = frappe.get_doc(DOCTYPE, doc.name)
        self._como(DPGC)
        d.estado = "Confirmado"
        with self.assertRaises(frappe.ValidationError):
            d.save(ignore_permissions=True)

    def test_lo_decidido_no_se_reescribe(self):
        doc = self._a(self._en_evaluacion(), "Confirmar", DPGC_2)
        self._sin_workflow()
        d = frappe.get_doc(DOCTYPE, doc.name)
        d.descripcion = "Otra versión de los hechos."
        with self.assertRaises(frappe.ValidationError):
            d.save(ignore_permissions=True)


class IntegrationTestEventoRiesgoConfirmacion(_Base):
    def test_confirmar_abre_la_no_conformidad_con_trazabilidad(self):
        doc = self._a(self._en_evaluacion(), "Confirmar", DPGC_2)
        self.assertEqual(doc.estado, "Confirmado")
        self.assertEqual(doc.evaluado_por, DPGC_2)
        self.assertTrue(doc.no_conformidad)

        nc = frappe.get_doc("No Conformidad", doc.no_conformidad)
        self.assertEqual((nc.origen_doctype, nc.origen_id), (DOCTYPE, doc.name))
        self.assertEqual(nc.origen_tipo, ORIGEN_NC)
        self.assertEqual(nc.tipo, "No conformidad mayor")
        self.assertEqual(nc.estado, "Abierta")
        self.assertEqual(nc.proceso, self.proceso)
        self.assertEqual(str(nc.fecha_deteccion), str(doc.fecha_evento))
        # Lo que hace falta para el análisis y el plan: el relato completo y la
        # exigencia de análisis de causas (#34).
        self.assertTrue(nc.requiere_analisis_causa)
        self.assertIn("Cola de estudiantes", nc.descripcion)
        self.assertIn("atención presencial", nc.descripcion)

    def test_la_no_conformidad_se_abre_una_sola_vez(self):
        doc = self._a(self._en_evaluacion(), "Confirmar", DPGC_2)
        d = frappe.get_doc(DOCTYPE, doc.name)
        self.assertEqual(d._abrir_no_conformidad(), doc.no_conformidad)
        self.assertEqual(
            frappe.db.count("No Conformidad", {"origen_doctype": DOCTYPE, "origen_id": doc.name}), 1)

    def test_respeta_el_tipo_elegido(self):
        doc = self._en_evaluacion()
        frappe.db.set_value(DOCTYPE, doc.name, "tipo_nc", "No conformidad menor")
        doc = self._a(doc, "Confirmar", DPGC_2)
        self.assertEqual(frappe.db.get_value("No Conformidad", doc.no_conformidad, "tipo"),
                         "No conformidad menor")


class IntegrationTestEventoRiesgoAvisos(_Base):
    def _para(self, regla, doc):
        notificacion = frappe.get_doc("Notification", regla)
        para, _cc, _cco = notificacion.get_list_of_recipients(doc, get_context(doc))
        return {c for c in para if c.endswith("@" + DOMINIO)}

    def test_las_reglas_existen(self):
        self.assertEqual(frappe.db.get_value("Notification", "SGC - Evento de riesgo reportado", "event"), "New")
        n = frappe.db.get_value("Notification", "SGC - Evento de riesgo decidido",
                                ["event", "value_changed", "channel"], as_dict=True)
        self.assertEqual((n.event, n.value_changed, n.channel), ("Value Change", "estado", "Email"))

    def test_el_reporte_avisa_a_la_dpgc(self):
        doc = frappe.get_doc({"doctype": DOCTYPE, "titulo": "x", "estado": "Reportado"})
        self.assertIn(DPGC, self._para("SGC - Evento de riesgo reportado", doc))

    def test_la_decision_avisa_a_quien_reporto(self):
        for estado, esperado in (("Confirmado", {COLAB}), ("Descartado", {COLAB}), ("En evaluacion", set())):
            with self.subTest(estado=estado):
                doc = frappe.get_doc({"doctype": DOCTYPE, "titulo": "x", "estado": estado,
                                      "reportado_por": COLAB})
                self.assertEqual(self._para("SGC - Evento de riesgo decidido", doc), esperado)


class IntegrationTestEventoRiesgoMenus(_Base):
    def test_el_riesgo_muestra_sus_eventos(self):
        enlaces = {(l.link_doctype, l.link_fieldname) for l in frappe.get_meta("Riesgo").links}
        self.assertIn((DOCTYPE, "riesgo"), enlaces)

    def test_esta_en_el_area_de_riesgos(self):
        self.assertIn(DOCTYPE, dict(f18_workspace.CARDS)["Riesgos y obligaciones"])
        barra = [d for _e, t, d in f18_workspace.SIDEBARS["SGC Riesgos"] if t == "DocType"]
        self.assertIn(DOCTYPE, barra)
