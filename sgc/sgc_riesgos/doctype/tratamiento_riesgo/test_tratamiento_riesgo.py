# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Suite de tests para el M14 — Tratamiento Riesgo (ISO 31000 §6.5).

El controlador aplica validaciones INCREMENTALES por etapa según el Select
`estado` (Planificado -> En ejecucion -> Implementado -> Verificado), sella
quién implementa y quién verifica, y prohíbe que sean la misma persona.

Tratamiento Riesgo tiene Workflow ("Tratamiento Riesgo SGC") -> se desactiva en
setUp para poder mover el estado directamente y dejar correr solo las
validaciones del CONTROLADOR. Ojo: sin workflow, la protección contra la
autoverificación que se prueba aquí es la ÚNICA que queda — y es justamente el
punto: el `allow_self_approval=0` del workflow no cubría este caso.

Todo lo que se prueba abajo sale de recorrer el flujo 14 en producción el
2026-08-23: el tratamiento llegaba a «Verificado» vacío, sin firma de nadie, y
verificado por el mismo usuario que constaba como responsable de implementarlo.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

ADMIN = "Administrator"
OTRO = "Guest"


class IntegrationTestTratamientoRiesgo(IntegrationTestCase):
    """Validaciones por etapa, sellos e independencia del verificador (M14)."""

    def setUp(self):
        factories.desactivar_workflow("Tratamiento Riesgo")
        factories.desactivar_workflow("Riesgo")

    # -- helpers ------------------------------------------------------------
    def _riesgo(self, estado="En tratamiento"):
        """Riesgo en el estado pedido, saltándose SUS guards a propósito.

        `Riesgo` exige desde el recorrido 13 que cada estado tenga detrás el
        registro que lo sostiene: «En tratamiento» pide que ya exista un
        `Tratamiento Riesgo`. Aquí eso sería circular —el tratamiento es
        justamente lo que se está probando—, y además lo que se prueba es el
        tratamiento, no el riesgo. Así que nace en «Identificado», que no exige
        nada, y el estado se fija por debajo del controlador.
        """
        doc = frappe.get_doc({
            "doctype": "Riesgo",
            "titulo": "Riesgo de prueba M14",
            "categoria": "Operacional",
            "estado": "Identificado",
        })
        doc.insert(ignore_permissions=True)
        if estado != "Identificado":
            frappe.db.set_value("Riesgo", doc.name, "estado", estado,
                                update_modified=False)
            doc.reload()
        return doc

    def _tratamiento(self, riesgo=None, plan=True, **overrides):
        """Tratamiento con el plan §6.5.3 completo salvo que se pida lo contrario."""
        vals = {
            "doctype": "Tratamiento Riesgo",
            "riesgo": riesgo or self._riesgo().name,
            "estado": "Planificado",
        }
        if plan:
            vals.update({
                "estrategia": "Reducir",
                "descripcion": "Doble validación del expediente antes de emitir.",
                "responsable": ADMIN,
                "fecha_compromiso": nowdate(),
            })
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.insert(ignore_permissions=True)
        return doc

    def _evidencia(self):
        return factories.crear_evidencia().name

    # ======================================================================
    # nivel >= 1 — En ejecucion: el plan de tratamiento (ISO 31000 §6.5.3)
    # ======================================================================
    # Se llegaba a «Verificado» sin estrategia, sin control descrito, sin
    # responsable y sin plazo. Eso no es un plan de tratamiento: es una casilla.

    def test_iniciar_sin_estrategia_falla(self):
        t = self._tratamiento(plan=False)
        t.estado = "En ejecucion"
        with self.assertRaises(frappe.ValidationError):
            t.save(ignore_permissions=True)

    def test_iniciar_sin_responsable_falla(self):
        t = self._tratamiento(responsable=None)
        t.estado = "En ejecucion"
        with self.assertRaises(frappe.ValidationError):
            t.save(ignore_permissions=True)

    def test_iniciar_sin_fecha_compromiso_falla(self):
        t = self._tratamiento(fecha_compromiso=None)
        t.estado = "En ejecucion"
        with self.assertRaises(frappe.ValidationError):
            t.save(ignore_permissions=True)

    def test_iniciar_con_el_plan_completo_ok(self):
        """El camino normal tiene que llegar: si no, el guard es un muro."""
        t = self._tratamiento()
        t.estado = "En ejecucion"
        t.save(ignore_permissions=True)

        self.assertEqual(t.estado, "En ejecucion")

    def test_planificado_vacio_se_guarda(self):
        """Planificar es borrador: ahí todavía no se exige nada."""
        t = self._tratamiento(plan=False)

        self.assertEqual(t.estado, "Planificado")

    # ======================================================================
    # nivel >= 2 — Implementado: el check que se marca el propio implementador
    # ======================================================================

    def test_implementar_sin_evidencia_falla(self):
        t = self._tratamiento(estado="En ejecucion")
        t.estado = "Implementado"
        with self.assertRaises(frappe.ValidationError):
            t.save(ignore_permissions=True)

    def test_implementar_con_evidencia_sella_quien_y_cuando(self):
        t = self._tratamiento(estado="En ejecucion")
        t.evidencia = self._evidencia()
        t.estado = "Implementado"
        t.save(ignore_permissions=True)

        self.assertEqual(t.implementado_por, frappe.session.user)
        self.assertEqual(str(t.fecha_implementacion), nowdate())

    def test_lo_que_alguien_escriba_en_implementado_por_no_prevalece(self):
        t = self._tratamiento(estado="En ejecucion")
        t.evidencia = self._evidencia()
        t.estado = "Implementado"
        t.implementado_por = OTRO
        t.save(ignore_permissions=True)

        self.assertEqual(t.implementado_por, frappe.session.user)

    # ======================================================================
    # nivel >= 3 — Verificado: evaluar la eficacia (ISO 9001:2015 §6.1.2 b)
    # ======================================================================

    def _implementado(self):
        t = self._tratamiento(estado="En ejecucion", responsable=OTRO)
        t.evidencia = self._evidencia()
        t.estado = "Implementado"
        t.save(ignore_permissions=True)
        # El sello lo pone la sesión (Administrator); para verificar hace falta
        # que el verificador NO sea el implementador.
        frappe.db.set_value("Tratamiento Riesgo", t.name, "implementado_por", OTRO,
                            update_modified=False)
        return frappe.get_doc("Tratamiento Riesgo", t.name)

    def test_verificar_sin_resultado_falla(self):
        t = self._implementado()
        t.nivel_residual = "Bajo"
        t.estado = "Verificado"
        with self.assertRaises(frappe.ValidationError):
            t.save(ignore_permissions=True)

    def test_verificar_sin_nivel_residual_falla(self):
        """El nivel residual es lo que el proceso 14 dice que registra."""
        t = self._implementado()
        t.resultado_verificacion = "Se revisaron 20 expedientes: ninguno sin doble firma."
        t.estado = "Verificado"
        with self.assertRaises(frappe.ValidationError):
            t.save(ignore_permissions=True)

    def test_verificar_completo_sella_quien_y_cuando(self):
        t = self._implementado()
        t.resultado_verificacion = "Se revisaron 20 expedientes: ninguno sin doble firma."
        t.nivel_residual = "Bajo"
        t.estado = "Verificado"
        t.save(ignore_permissions=True)

        self.assertEqual(t.estado, "Verificado")
        self.assertEqual(t.verificado_por, frappe.session.user)
        self.assertEqual(str(t.fecha_verificacion), nowdate())

    def test_lo_que_alguien_escriba_en_verificado_por_no_prevalece(self):
        t = self._implementado()
        t.resultado_verificacion = "Comprobado contra la muestra."
        t.nivel_residual = "Bajo"
        t.verificado_por = OTRO
        t.estado = "Verificado"
        t.save(ignore_permissions=True)

        self.assertEqual(t.verificado_por, frappe.session.user)

    # ======================================================================
    # Independencia: quien implementa no verifica
    # ======================================================================
    # El caso exacto del recorrido: el Dueño de Proceso creó el tratamiento y
    # puso de responsable a un usuario con rol DPGC; ese usuario verificó su
    # propio trabajo. `allow_self_approval=0` no lo vio porque Frappe solo
    # compara con `doc.owner`, y el owner era otro.

    def test_el_responsable_no_puede_verificar_su_tratamiento(self):
        t = self._tratamiento(estado="En ejecucion", responsable=frappe.session.user)
        t.evidencia = self._evidencia()
        t.estado = "Implementado"
        t.save(ignore_permissions=True)

        t.resultado_verificacion = "Todo correcto."
        t.nivel_residual = "Bajo"
        t.estado = "Verificado"
        with self.assertRaises(frappe.ValidationError):
            t.save(ignore_permissions=True)

    def test_quien_lo_implemento_no_puede_verificar_aunque_cambie_el_responsable(self):
        """`responsable` es tecleable hasta el final; el sello no."""
        t = self._tratamiento(estado="En ejecucion", responsable=frappe.session.user)
        t.evidencia = self._evidencia()
        t.estado = "Implementado"
        t.save(ignore_permissions=True)

        t.responsable = OTRO          # se quita de en medio justo antes de verificar
        t.resultado_verificacion = "Todo correcto."
        t.nivel_residual = "Bajo"
        t.estado = "Verificado"
        with self.assertRaises(frappe.ValidationError):
            t.save(ignore_permissions=True)

    # ======================================================================
    # La vuelta «Verificar no eficaz» (Implementado -> En ejecucion)
    # ======================================================================
    # Existe y funciona (comprobada en vivo el 2026-08-23), pero devolvía el
    # tratamiento a ejecución sin decir por qué y dejando pegado el sello de la
    # implementación que acababa de declararse inservible.

    def test_devolver_por_no_eficaz_exige_motivo(self):
        t = self._implementado()
        t.estado = "En ejecucion"
        with self.assertRaises(frappe.ValidationError):
            t.save(ignore_permissions=True)

    def test_devolver_por_no_eficaz_registra_verificador_y_limpia_la_implementacion(self):
        t = self._implementado()
        t.resultado_verificacion = "El control no se aplicó en 6 de 20 expedientes."
        t.estado = "En ejecucion"
        t.save(ignore_permissions=True)

        self.assertEqual(t.estado, "En ejecucion")
        self.assertEqual(t.verificado_por, frappe.session.user)
        self.assertIsNone(t.implementado_por)
        self.assertIsNone(t.fecha_implementacion)

    def test_quien_implemento_tampoco_declara_no_eficaz(self):
        t = self._tratamiento(estado="En ejecucion", responsable=frappe.session.user)
        t.evidencia = self._evidencia()
        t.estado = "Implementado"
        t.save(ignore_permissions=True)

        t.resultado_verificacion = "No funcionó."
        t.estado = "En ejecucion"
        with self.assertRaises(frappe.ValidationError):
            t.save(ignore_permissions=True)

    def test_la_segunda_vuelta_sella_a_quien_reimplementa(self):
        """Tras devolver, el sello viejo no puede quedarse pegado."""
        t = self._implementado()
        t.resultado_verificacion = "El control no se aplicó en 6 de 20 expedientes."
        t.estado = "En ejecucion"
        t.save(ignore_permissions=True)

        t.estado = "Implementado"
        t.save(ignore_permissions=True)

        self.assertEqual(t.implementado_por, frappe.session.user)

    # ======================================================================
    # Coherencia con el riesgo padre
    # ======================================================================

    def test_no_se_crea_un_tratamiento_sobre_un_riesgo_cerrado(self):
        """«Cerrado» es terminal en el workflow del riesgo: no admite más trabajo."""
        riesgo = self._riesgo(estado="Cerrado")
        with self.assertRaises(frappe.ValidationError):
            self._tratamiento(riesgo=riesgo.name)

    def test_un_tratamiento_en_marcha_sobrevive_al_cierre_del_riesgo(self):
        """El riesgo cerrado no debe dejar colgado lo que ya estaba en marcha:
        «Cerrado» no tiene vuelta atrás, así que bloquear aquí sería una trampa."""
        riesgo = self._riesgo()
        t = self._tratamiento(riesgo=riesgo.name, estado="En ejecucion")
        frappe.db.set_value("Riesgo", riesgo.name, "estado", "Cerrado",
                            update_modified=False)

        t.evidencia = self._evidencia()
        t.estado = "Implementado"
        t.save(ignore_permissions=True)

        self.assertEqual(t.estado, "Implementado")
