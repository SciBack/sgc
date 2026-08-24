# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Suite del flujo 13 — Riesgo (GRC, ISO 31000 / ISO 9001 §6.1 y §10.2).

Todo lo que se verifica aquí nació del recorrido del flujo en producción del
2026-08-23, donde un riesgo recorría el ciclo entero sin ningún registro detrás
y la cadena riesgo materializado -> no conformidad estaba escrita pero muerta:

  - Guardas incrementales por estado: «Evaluado» exige una `Evaluacion Riesgo`,
    «En tratamiento» exige un `Tratamiento Riesgo`.
  - Cierre desde «Monitoreado»: ningún tratamiento sin verificar.
  - Cierre desde «Materializado»: la No Conformidad tiene que existir y estar
    cerrada.
  - Entrar en «Materializado» crea la No Conformidad (idempotente), que es lo
    que `sgc/bpmn.py` ya declaraba y no ocurría.

`Riesgo`, `Tratamiento Riesgo` y `No Conformidad` tienen Workflow activo: se
desactivan en setUp para poder mover el estado libremente y ejercitar el
CONTROLADOR, que es lo que se está probando.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestRiesgo(IntegrationTestCase):
    def setUp(self):
        factories.desactivar_workflow("Riesgo")
        factories.desactivar_workflow("Tratamiento Riesgo")
        factories.desactivar_workflow("No Conformidad")

    # -- helpers ------------------------------------------------------------
    def _riesgo(self, **overrides):
        vals = {
            "doctype": "Riesgo",
            "titulo": "Riesgo de prueba del flujo 13",
            "descripcion": "evento incierto de prueba",
            "categoria": "Operacional",
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _evaluacion(self, riesgo, probabilidad=3, impacto=3):
        doc = frappe.get_doc({
            "doctype": "Evaluacion Riesgo",
            "riesgo": riesgo.name,
            "momento": "Inherente",
            "fecha": frappe.utils.nowdate(),
            "probabilidad": probabilidad,
            "impacto": impacto,
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _tratamiento(self, riesgo, estado="Planificado"):
        """Tratamiento en el estado pedido, cumpliendo lo que ese estado exige.

        `Tratamiento Riesgo` valida de forma incremental (plan completo para
        ejecutar, evidencia para implementar, resultado y nivel residual para
        verificar), así que un tratamiento de prueba no puede nacer en
        «Verificado» con dos campos: lo rechaza su propio controlador. Aquí
        interesa el riesgo, no el tratamiento, de modo que se rellena lo que
        cada etapa pide y se acabó.
        """
        vals = {
            "doctype": "Tratamiento Riesgo",
            "riesgo": riesgo.name,
            "estrategia": "Reducir",
            "descripcion": "control de prueba",
            "estado": estado,
        }
        if estado != "Planificado":
            vals.update({
                # El responsable NO puede ser quien corre el test: desde el
                # recorrido 14, quien implementa un tratamiento no puede
                # verificarlo, y estos tests insertan directamente en
                # «Verificado» actuando como Administrator.
                "responsable": "Guest",
                "fecha_compromiso": add_days(nowdate(), 30),
            })
        if estado in ("Implementado", "Verificado"):
            vals["evidencia"] = self._evidencia()
        if estado == "Verificado":
            vals.update({
                "resultado_verificacion": "Control operando; se revisaron los registros.",
                "nivel_residual": "Bajo",
            })
        doc = frappe.get_doc(vals)
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _evidencia(self):
        """Evidencia mínima que sirva de prueba de implementación."""
        doc = frappe.get_doc({
            "doctype": "Evidencia",
            "titulo": "Prueba de implementación del control",
            "tipo": "Enlace",
            "enlace_url": "https://ejemplo.edu.pe/evidencia",
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc.name

    def _mover(self, riesgo, estado):
        riesgo.estado = estado
        riesgo.save(ignore_permissions=True)
        return riesgo

    def _hasta_monitoreado(self, tratamiento_estado="Verificado"):
        r = self._riesgo()
        self._evaluacion(r)
        self._tratamiento(r, estado=tratamiento_estado)
        self._mover(r, "Evaluado")
        self._mover(r, "En tratamiento")
        return self._mover(r, "Monitoreado")

    # ======================================================================
    # Guardas incrementales por estado
    # ======================================================================
    def test_evaluado_exige_evaluacion(self):
        r = self._riesgo()
        with self.assertRaises(frappe.ValidationError):
            self._mover(r, "Evaluado")

    def test_evaluado_pasa_con_evaluacion(self):
        r = self._riesgo()
        self._evaluacion(r)
        self.assertEqual(self._mover(r, "Evaluado").estado, "Evaluado")

    def test_en_tratamiento_exige_tratamiento(self):
        r = self._riesgo()
        self._evaluacion(r)
        self._mover(r, "Evaluado")
        with self.assertRaises(frappe.ValidationError):
            self._mover(r, "En tratamiento")

    def test_en_tratamiento_pasa_con_tratamiento(self):
        r = self._riesgo()
        self._evaluacion(r)
        self._tratamiento(r)
        self._mover(r, "Evaluado")
        self.assertEqual(self._mover(r, "En tratamiento").estado, "En tratamiento")

    # ======================================================================
    # Cierre desde «Monitoreado»: eficacia comprobada (ISO 9001 §6.1.2 b)
    # ======================================================================
    def test_no_cierra_con_tratamiento_sin_verificar(self):
        r = self._hasta_monitoreado(tratamiento_estado="Implementado")
        with self.assertRaises(frappe.ValidationError):
            self._mover(r, "Cerrado")

    def test_cierra_con_todos_los_tratamientos_verificados(self):
        r = self._hasta_monitoreado(tratamiento_estado="Verificado")
        self.assertEqual(self._mover(r, "Cerrado").estado, "Cerrado")

    # ======================================================================
    # El dueño del riesgo no ejerce el control sobre su propio riesgo
    # ======================================================================
    def test_el_propietario_no_cierra_su_riesgo(self):
        """`allow_self_approval=0` mira `doc.owner`, no el campo `propietario`."""
        r = self._hasta_monitoreado()
        frappe.db.set_value("Riesgo", r.name, "propietario", frappe.session.user)
        r.reload()
        with self.assertRaises(frappe.ValidationError):
            self._mover(r, "Cerrado")

    def test_el_propietario_no_materializa_su_riesgo(self):
        r = self._hasta_monitoreado()
        frappe.db.set_value("Riesgo", r.name, "propietario", frappe.session.user)
        r.reload()
        with self.assertRaises(frappe.ValidationError):
            self._mover(r, "Materializado")

    def test_otro_usuario_si_cierra(self):
        r = self._hasta_monitoreado()
        frappe.db.set_value("Riesgo", r.name, "propietario", "Guest")
        r.reload()
        self.assertEqual(self._mover(r, "Cerrado").estado, "Cerrado")

    # ======================================================================
    # Materialización -> No Conformidad (ISO 9001 §10.2)
    # ======================================================================
    def test_materializar_crea_la_no_conformidad(self):
        r = self._hasta_monitoreado()
        self._mover(r, "Materializado")
        nc = frappe.db.get_value(
            "No Conformidad",
            {"origen_doctype": "Riesgo", "origen_id": r.name},
            ["name", "origen_tipo", "tipo", "estado"],
            as_dict=True,
        )
        self.assertIsNotNone(nc)
        self.assertEqual(nc.origen_tipo, "Riesgo materializado")
        self.assertEqual(nc.estado, "Abierta")

    def test_escalamiento_idempotente(self):
        r = self._hasta_monitoreado()
        self._mover(r, "Materializado")
        primera = frappe.db.get_value(
            "No Conformidad", {"origen_doctype": "Riesgo", "origen_id": r.name}, "name"
        )
        # Reguardar un riesgo ya materializado no crea una segunda NC.
        r.save(ignore_permissions=True)
        self.assertEqual(r.escalar_a_no_conformidad(), primera)
        self.assertEqual(
            frappe.db.count("No Conformidad", {"origen_doctype": "Riesgo", "origen_id": r.name}), 1
        )

    def test_solo_escala_un_riesgo_materializado(self):
        r = self._hasta_monitoreado()
        with self.assertRaises(frappe.ValidationError):
            r.escalar_a_no_conformidad()

    def test_no_cierra_materializado_con_nc_abierta(self):
        r = self._hasta_monitoreado()
        self._mover(r, "Materializado")
        with self.assertRaises(frappe.ValidationError):
            self._mover(r, "Cerrado")

    def test_cierra_materializado_con_nc_cerrada(self):
        r = self._hasta_monitoreado()
        self._mover(r, "Materializado")
        nc = frappe.db.get_value(
            "No Conformidad", {"origen_doctype": "Riesgo", "origen_id": r.name}, "name"
        )
        # `set_value` directo: cerrar la NC por su propio ciclo pide evidencia de
        # cierre y aquí lo que se prueba es la guarda del riesgo, no la de la NC.
        frappe.db.set_value("No Conformidad", nc, "estado", "Cerrada eficaz")
        self.assertEqual(self._mover(r, "Cerrado").estado, "Cerrado")

    def test_no_cierra_materializado_sin_no_conformidad(self):
        r = self._hasta_monitoreado()
        self._mover(r, "Materializado")
        nc = frappe.db.get_value(
            "No Conformidad", {"origen_doctype": "Riesgo", "origen_id": r.name}, "name"
        )
        frappe.delete_doc("No Conformidad", nc, force=True, ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            self._mover(r, "Cerrado")
