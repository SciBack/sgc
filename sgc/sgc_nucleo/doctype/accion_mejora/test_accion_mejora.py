# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Suite de tests del M11 — Accion Mejora (la acción correctiva de ISO 9001 §10.2).

Lo que ejercita, todo salido del recorrido del flujo 12 sobre producción del
2026-08-23 (`docs/diagramas/bpmn/12-accion-mejora.bpmn`):

  before_insert:
    sin `codigo`                        -> lo compone AM-{anio}-NNNN

  Exigencias de cada transición (solo al CAMBIAR de estado):
    -> "En ejecucion"                   sin responsable            -> falla
    -> "En ejecucion"                   sin fecha_compromiso (ETA) -> falla
    -> "Verificada eficaz"              sin evidencia_cierre       -> falla
    ya "Verificada eficaz"              quitando la evidencia      -> falla
    alta directa en estado avanzado     no exige nada (semilla/migración)

  Registro de quién verifica:
    entrar en "Verificada eficaz" / "Verificada no eficaz" sella `verificada_por`
    con `frappe.session.user`, y lo que alguien teclee ahí no prevalece.

  Avance:
    salir de un estado que fijaba 100 (Verificar no eficaz / Reabrir) limpia el
    100 heredado, y el plan padre deja de anunciar una acción fallida como
    completa.

El rollup al `Plan Mejora` (promedio, semáforo, fecha) vive en
`test_plan_mejora.py`; aquí solo se comprueba lo que el avance de la acción le
hace llegar.

Hereda de `IntegrationTestCase`: cada test corre en su transacción con rollback.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

# Usuario siempre presente en Frappe; sirve de Link para responsable.
ADMIN = "Administrator"


class IntegrationTestAccionMejora(IntegrationTestCase):
    """Guardas de etapa, sello del verificador y avance de la Accion Mejora."""

    def setUp(self):
        # Accion Mejora tiene Workflow activo en producción (f4). Los tests mueven
        # el `estado` a mano para ejercitar el CONTROLADOR, que es lo que se está
        # probando; el workflow se reactiva solo con el rollback del test.
        factories.desactivar_workflow("Accion Mejora")
        factories.desactivar_workflow("Plan Mejora")
        self.evidencia = factories.crear_evidencia().name

    # -- helpers -----------------------------------------------------------
    def _accion(self, **overrides):
        """Acción planificada con lo mínimo para poder iniciarla."""
        vals = {
            "doctype": "Accion Mejora",
            "descripcion": "Acción de mejora de prueba M11",
            "tipo": "Correctiva",
            "estado": "Planificada",
            "responsable": ADMIN,
            "fecha_compromiso": add_days(nowdate(), 30),
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _mover(self, acc, estado, **campos):
        """Cambia de estado como lo hace el workflow: un save sobre el doc vivo."""
        acc.estado = estado
        for k, v in campos.items():
            acc.set(k, v)
        acc.flags.ignore_permissions = True
        acc.save(ignore_permissions=True)
        return acc

    def _ejecutada(self, **overrides):
        acc = self._accion(**overrides)
        self._mover(acc, "En ejecucion")
        self._mover(acc, "Ejecutada")
        return acc

    # ======================================================================
    # before_insert
    # ======================================================================
    def test_se_crea_sin_codigo_y_lo_compone_el_doctype(self):
        """`autoname: field:codigo` y hasta el 2026-08-23 solo `capa.py` lo ponía:
        crearla por cualquier otra vía fallaba con «Código is required»."""
        acc = self._accion()
        self.assertTrue(acc.codigo.startswith(f"AM-{nowdate()[:4]}-"))
        self.assertEqual(acc.name, acc.codigo)

    # ======================================================================
    # Exigencias de cada transición
    # ======================================================================
    def test_iniciar_sin_responsable_falla(self):
        acc = self._accion(responsable=None)
        with self.assertRaises(frappe.ValidationError):
            self._mover(acc, "En ejecucion")

    def test_iniciar_sin_fecha_compromiso_falla(self):
        """Sin ETA la acción no entra en el semáforo del plan ni genera aviso."""
        acc = self._accion(fecha_compromiso=None)
        with self.assertRaises(frappe.ValidationError):
            self._mover(acc, "En ejecucion")

    def test_iniciar_con_responsable_y_eta_pasa(self):
        acc = self._accion()
        self._mover(acc, "En ejecucion")
        self.assertEqual(acc.estado, "En ejecucion")

    def test_alta_directa_en_estado_avanzado_no_exige_nada(self):
        """Una semilla/migración que aterriza ya avanzada no es un acto de nadie:
        el control es de la TRANSICIÓN, no del guardado."""
        acc = self._accion(estado="En ejecucion", responsable=None,
                           fecha_compromiso=None)
        self.assertEqual(acc.estado, "En ejecucion")

    def test_verificar_eficaz_sin_evidencia_falla(self):
        """ISO 9001:2015 §10.2.2: hay que conservar información documentada de
        los resultados de la acción correctiva."""
        acc = self._ejecutada()
        with self.assertRaises(frappe.ValidationError):
            self._mover(acc, "Verificada eficaz")

    def test_verificar_eficaz_con_evidencia_pasa(self):
        acc = self._ejecutada()
        self._mover(acc, "Verificada eficaz", evidencia_cierre=self.evidencia)
        self.assertEqual(acc.estado, "Verificada eficaz")

    def test_verificar_no_eficaz_no_exige_evidencia(self):
        """Exigirla aquí solo empujaría a NO registrar la verificación fallida:
        el que no cierra nada es el «no eficaz»."""
        acc = self._ejecutada()
        self._mover(acc, "Verificada no eficaz")
        self.assertEqual(acc.estado, "Verificada no eficaz")

    def test_no_se_puede_quitar_la_evidencia_de_un_cierre_eficaz(self):
        acc = self._ejecutada()
        self._mover(acc, "Verificada eficaz", evidencia_cierre=self.evidencia)
        with self.assertRaises(frappe.ValidationError):
            self._mover(acc, "Verificada eficaz", evidencia_cierre=None)

    # ======================================================================
    # Quién verifica
    # ======================================================================
    def test_verificar_registra_a_quien_verifica(self):
        """El recorrido del 2026-08-23: cerró la DPGC, después el responsable
        editó la acción cerrada y `modified_by` pasó a ser él. Del verificador no
        quedaba nada en el documento."""
        acc = self._ejecutada()
        self._mover(acc, "Verificada eficaz", evidencia_cierre=self.evidencia)
        self.assertEqual(acc.verificada_por, frappe.session.user)

    def test_verificar_no_eficaz_tambien_registra_a_quien_verifica(self):
        acc = self._ejecutada()
        self._mover(acc, "Verificada no eficaz")
        self.assertEqual(acc.verificada_por, frappe.session.user)

    def test_lo_tecleado_a_mano_no_prevalece(self):
        acc = self._ejecutada()
        self._mover(acc, "Verificada eficaz", evidencia_cierre=self.evidencia,
                    verificada_por="Guest")
        self.assertEqual(acc.verificada_por, frappe.session.user)

    def test_quedarse_verificada_no_reescribe_la_firma(self):
        """Se sella al ENTRAR: editar después la acción cerrada no cambia quién
        la verificó (eso es justo lo que pasó en el recorrido con modified_by)."""
        acc = self._ejecutada()
        self._mover(acc, "Verificada eficaz", evidencia_cierre=self.evidencia)
        frappe.db.set_value("Accion Mejora", acc.name, "verificada_por", "Guest",
                            update_modified=False)

        acc = frappe.get_doc("Accion Mejora", acc.name)
        acc.descripcion = "Descripción corregida por el responsable."
        acc.save(ignore_permissions=True)

        self.assertEqual(acc.verificada_por, "Guest")

    def test_reabrir_borra_la_firma_de_la_verificacion_anterior(self):
        """Una acción de vuelta en ejecución no está verificada por nadie."""
        acc = self._ejecutada()
        self._mover(acc, "Verificada no eficaz")
        self.assertEqual(acc.verificada_por, frappe.session.user)

        self._mover(acc, "En ejecucion")          # Reabrir
        self.assertFalse(acc.verificada_por)

    def test_una_accion_sin_verificar_no_tiene_verificador(self):
        acc = self._ejecutada()
        self.assertFalse(acc.verificada_por)

    def test_reverificar_tras_reabrir_registra_al_verificador_de_esta_vez(self):
        """La acción de mejora es el ÚNICO documento del CAPA que puede volver
        de un «no eficaz»: cada vuelta tiene su propio verificador."""
        acc = self._ejecutada()
        self._mover(acc, "Verificada no eficaz")
        frappe.db.set_value("Accion Mejora", acc.name, "verificada_por", "Guest",
                            update_modified=False)

        acc = frappe.get_doc("Accion Mejora", acc.name)
        self._mover(acc, "En ejecucion")          # Reabrir
        self._mover(acc, "Ejecutada")
        self._mover(acc, "Verificada eficaz", evidencia_cierre=self.evidencia)

        self.assertEqual(acc.verificada_por, frappe.session.user)

    # ======================================================================
    # Avance
    # ======================================================================
    def test_verificar_no_eficaz_limpia_el_100_heredado(self):
        acc = self._ejecutada()
        self.assertEqual(acc.avance_pct, 100)

        self._mover(acc, "Verificada no eficaz")
        self.assertEqual(acc.avance_pct, 0)

    def test_reabrir_no_arrastra_el_avance_completo(self):
        """En el recorrido, la acción volvió a «En ejecucion» con avance 100 y el
        plan siguió anunciando 100 % mientras se rehacía."""
        acc = self._ejecutada()
        self._mover(acc, "Verificada no eficaz")
        self._mover(acc, "En ejecucion")          # Reabrir
        self.assertEqual(acc.avance_pct, 0)

    def test_el_plan_padre_deja_de_anunciar_completa_una_accion_fallida(self):
        plan = frappe.get_doc({
            "doctype": "Plan Mejora",
            "titulo": "Plan de prueba del rollup tras un no eficaz",
            "estado": "En ejecucion",
        })
        plan.flags.ignore_permissions = True
        plan.insert(ignore_permissions=True)

        acc = self._ejecutada(plan_mejora=plan.name)
        self.assertEqual(frappe.db.get_value("Plan Mejora", plan.name, "avance_pct"), 100)

        self._mover(acc, "Verificada no eficaz")
        self.assertEqual(frappe.db.get_value("Plan Mejora", plan.name, "avance_pct"), 0)

    def test_el_avance_manual_sobrevive_al_cambio_de_estado(self):
        """Solo se limpia el 100 heredado; un % que declaró el responsable, no."""
        acc = self._accion()
        self._mover(acc, "En ejecucion", avance_pct=40)
        self.assertEqual(acc.avance_pct, 40)

    def test_estados_terminales_siguen_fijando_su_avance(self):
        acc = self._accion(avance_pct=80)
        self.assertEqual(acc.avance_pct, 0)       # Planificada fuerza 0
        self._mover(acc, "En ejecucion")
        self._mover(acc, "Ejecutada", avance_pct=5)
        self.assertEqual(acc.avance_pct, 100)     # Ejecutada fuerza 100
