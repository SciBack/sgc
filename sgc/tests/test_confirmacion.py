# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Suite de integración para `sgc/confirmacion.py` — cierre humano de la cadena F2.

El motor (`scoring.py`) solo PROPONE (`Valoracion Estandar.nivel_propuesto`); este
módulo es la ACCIÓN HUMANA que confirma el `nivel` oficial (NL/L/LP, permlevel 1) y,
tras confirmar los 10 estándares, promueve la vigencia oficial de la autoevaluación.

Cada test corre en su propia transacción (rollback automático de `IntegrationTestCase`).

Convenciones respetadas:
  - Las funciones whitelisted se invocan como funciones Python normales (import directo).
    La restricción por ROL del whitelist se salta ejecutando como `Administrator`
    (fijado en `setUp`); además `confirmar_nivel` escribe con `ignore_permissions=True`
    dentro de la propia función.
  - `Autoevaluacion` tiene Workflow ACTIVO: se desactiva en `setUp` porque
    `finalizar_vigencia` toca `Autoevaluacion.resultado_vigencia`.
  - La escala NL/L/LP la aporta `factories.crear_marco_prueba(con_escala=True)`.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc import confirmacion
from sgc.tests import factories


class IntegrationTestConfirmacion(IntegrationTestCase):
    """Confirmación humana del nivel oficial y promoción de la vigencia (F2)."""

    PREFIJO = "TEST-CONF"

    def setUp(self):
        # Autoevaluacion tiene Workflow activo; finalizar_vigencia escribe en ella.
        factories.desactivar_workflow("Autoevaluacion")
        # Las funciones usan `frappe.session.user` para `aprobado_por` y el whitelist
        # se restringe por ROL: ejecutamos como Administrator para saltar la restricción.
        self._usuario_previo = frappe.session.user
        frappe.set_user("Administrator")

        # Árbol base: marco con 3 estándares × 3 criterios + escala NL/L/LP.
        self.arbol = factories.crear_marco_prueba(
            n_estandares=3, n_criterios=3, prefijo=self.PREFIJO
        )
        self.marco = self.arbol["marco"]
        self.estandares = self.arbol["estandares"]        # ["TEST-CONF-E1", ...]
        self.criterios = self.arbol["criterios"]          # {est: [criterios]}
        self.ae = factories.crear_autoevaluacion(self.marco, prefijo=self.PREFIJO).name

    def tearDown(self):
        # Restaurar el usuario para no filtrar la sesión Administrator a otros casos.
        frappe.set_user(self._usuario_previo)

    # -- helpers de lectura -------------------------------------------------
    def _valoracion(self, estandar):
        """Devuelve el doc `Valoracion Estandar` del par (autoevaluacion, estandar)."""
        name = frappe.db.get_value(
            "Valoracion Estandar",
            {"autoevaluacion": self.ae, "elemento_marco": estandar},
            "name",
        )
        return frappe.get_doc("Valoracion Estandar", name) if name else None

    def _sigla_de_nivel(self, nivel_name):
        """Sigla (NL/L/LP) del `Nivel Escala` referenciado por `nivel_name`."""
        return frappe.db.get_value("Nivel Escala", nivel_name, "sigla")

    # ======================================================================
    # confirmar_nivel — fija el nivel oficial + confirmado + comentario
    # ======================================================================
    def test_confirmar_nivel_fija_oficial_confirmado_y_comentario(self):
        """Confirma L: deja `nivel`=L, `confirmado=1`, `aprobado_por` y guarda el comentario."""
        est = self.estandares[0]
        res = confirmacion.confirmar_nivel(
            self.ae, est, "L", comentario="Revisado por el comité de calidad."
        )

        self.assertTrue(res["ok"])
        self.assertEqual(res["sigla"], "L")
        self.assertFalse(res["override"])  # no había propuesta, no es override

        ve = self._valoracion(est)
        self.assertIsNotNone(ve)
        self.assertEqual(self._sigla_de_nivel(ve.nivel), "L")   # nivel oficial NL/L/LP
        self.assertEqual(ve.confirmado, 1)
        self.assertEqual(ve.aprobado_por, "Administrator")
        self.assertEqual(ve.justificacion, "Revisado por el comité de calidad.")
        if ve.meta.has_field("estado"):
            self.assertEqual(ve.estado, "Aprobado")

    def test_confirmar_nivel_acepta_las_tres_siglas(self):
        """Cada sigla de la escala (NL/L/LP) se resuelve a su `Nivel Escala` oficial."""
        for i, sigla in enumerate(("NL", "L", "LP")):
            est = self.estandares[i]
            confirmacion.confirmar_nivel(self.ae, est, sigla)
            ve = self._valoracion(est)
            self.assertEqual(self._sigla_de_nivel(ve.nivel), sigla)
            self.assertEqual(ve.confirmado, 1)

    def test_confirmar_nivel_es_override_cuando_difiere_del_propuesto(self):
        """Si el humano confirma distinto al `nivel_propuesto` del motor -> override con traza."""
        est = self.estandares[0]
        # Todos "Cumple" -> el motor propone LP.
        factories.valorar_estandar(self.ae, self.criterios[est], default=factories.CUMPLE)
        self.assertEqual(self._valoracion(est).nivel_propuesto, "LP")

        # El humano confirma L (override, sin comentario) -> justificacion autogenerada.
        res = confirmacion.confirmar_nivel(self.ae, est, "L")

        self.assertTrue(res["override"])
        self.assertEqual(res["propuesto"], "LP")
        ve = self._valoracion(est)
        self.assertEqual(self._sigla_de_nivel(ve.nivel), "L")
        self.assertTrue(ve.justificacion)  # se dejó traza del override
        self.assertIn("Override", ve.justificacion)

    def test_confirmar_nivel_es_idempotente(self):
        """Reconfirmar el mismo nivel no rompe ni duplica la Valoracion Estandar."""
        est = self.estandares[0]
        confirmacion.confirmar_nivel(self.ae, est, "LP")
        confirmacion.confirmar_nivel(self.ae, est, "LP")

        filas = frappe.get_all(
            "Valoracion Estandar",
            filters={"autoevaluacion": self.ae, "elemento_marco": est},
            pluck="name",
        )
        self.assertEqual(len(filas), 1)
        ve = self._valoracion(est)
        self.assertEqual(self._sigla_de_nivel(ve.nivel), "LP")
        self.assertEqual(ve.confirmado, 1)

    # ======================================================================
    # confirmar_nivel — errores
    # ======================================================================
    def test_confirmar_nivel_sigla_invalida_lanza(self):
        """Una sigla fuera de NL/L/LP se rechaza con ValidationError."""
        est = self.estandares[0]
        with self.assertRaises(frappe.exceptions.ValidationError):
            confirmacion.confirmar_nivel(self.ae, est, "XX")
        # No debe haber quedado ninguna Valoracion Estandar creada.
        self.assertIsNone(self._valoracion(est))

    def test_confirmar_nivel_argumentos_vacios_lanza(self):
        """Faltando `autoevaluacion` o `estandar` la función corta con throw."""
        with self.assertRaises(frappe.exceptions.ValidationError):
            confirmacion.confirmar_nivel(None, self.estandares[0], "L")
        with self.assertRaises(frappe.exceptions.ValidationError):
            confirmacion.confirmar_nivel(self.ae, None, "L")

    def test_confirmar_nivel_autoevaluacion_inexistente_lanza(self):
        """Un `autoevaluacion` inexistente falla al validar el Link al persistir."""
        with self.assertRaises(frappe.exceptions.ValidationError):
            confirmacion.confirmar_nivel("AE-NO-EXISTE-999", self.estandares[0], "L")

    # ======================================================================
    # confirmar_todos_propuestos — confirmación en bloque
    # ======================================================================
    def test_confirmar_todos_propuestos_confirma_los_con_propuesta(self):
        """Confirma en bloque cada estándar con `nivel_propuesto`; devuelve cuántos."""
        e1, e2, e3 = self.estandares
        # E1 todos Cumple -> LP ; E2 un No cumple -> NL ; E3 un parcial -> L.
        factories.valorar_estandar(self.ae, self.criterios[e1], default=factories.CUMPLE)
        factories.valorar_estandar(self.ae, self.criterios[e2], juicios={0: factories.NO_CUMPLE})
        factories.valorar_estandar(self.ae, self.criterios[e3], juicios={0: factories.CUMPLE_PARCIAL})

        res = confirmacion.confirmar_todos_propuestos(self.ae)

        self.assertTrue(res["ok"])
        self.assertEqual(res["confirmados"], 3)
        # Cada estándar quedó con su nivel propuesto confirmado como oficial.
        self.assertEqual(self._sigla_de_nivel(self._valoracion(e1).nivel), "LP")
        self.assertEqual(self._sigla_de_nivel(self._valoracion(e2).nivel), "NL")
        self.assertEqual(self._sigla_de_nivel(self._valoracion(e3).nivel), "L")
        for est in self.estandares:
            self.assertEqual(self._valoracion(est).confirmado, 1)

    def test_confirmar_todos_propuestos_salta_los_sin_propuesta(self):
        """Solo confirma los estándares con `nivel_propuesto`; los demás se ignoran."""
        e1, e2, e3 = self.estandares
        # Solo E1 recibe valoración -> solo E1 obtiene nivel_propuesto (LP).
        factories.valorar_estandar(self.ae, self.criterios[e1], default=factories.CUMPLE)

        res = confirmacion.confirmar_todos_propuestos(self.ae)

        self.assertEqual(res["confirmados"], 1)
        self.assertEqual(self._valoracion(e1).confirmado, 1)
        # E2 y E3 no tenían propuesta -> no se creó/confirmó su Valoracion Estandar.
        self.assertIsNone(self._valoracion(e2))
        self.assertIsNone(self._valoracion(e3))

    def test_confirmar_todos_propuestos_sin_ninguna_propuesta(self):
        """Sin valoraciones no hay propuestas -> confirmados=0 (no lanza)."""
        res = confirmacion.confirmar_todos_propuestos(self.ae)
        self.assertTrue(res["ok"])
        self.assertEqual(res["confirmados"], 0)

    def test_confirmar_todos_propuestos_es_idempotente(self):
        """Una segunda pasada no reconfirma lo ya confirmado (confirmados=0)."""
        e1 = self.estandares[0]
        factories.valorar_estandar(self.ae, self.criterios[e1], default=factories.CUMPLE)
        primera = confirmacion.confirmar_todos_propuestos(self.ae)
        segunda = confirmacion.confirmar_todos_propuestos(self.ae)
        self.assertEqual(primera["confirmados"], 1)
        self.assertEqual(segunda["confirmados"], 0)

    def test_confirmar_todos_propuestos_sin_autoevaluacion_lanza(self):
        """Sin `autoevaluacion` la función corta con throw."""
        with self.assertRaises(frappe.exceptions.ValidationError):
            confirmacion.confirmar_todos_propuestos(None)

    # ======================================================================
    # finalizar_vigencia — promueve la vigencia oficial (Tabla 9)
    # ======================================================================
    def test_finalizar_vigencia_marca_acreditado_6_anios(self):
        """10/10 confirmados en LP -> vigencia oficial "Acreditado 6 años"."""
        arbol = factories.crear_marco_prueba(
            n_estandares=confirmacion.TOTAL_ESTANDARES, n_criterios=1, prefijo="TEST-FIN6"
        )
        ae = factories.crear_autoevaluacion(arbol, prefijo="TEST-FIN6").name
        for est in arbol["estandares"]:
            factories.confirmar_estandar(ae, est, "LP", prefijo="TEST-FIN6")

        res = confirmacion.finalizar_vigencia(ae)

        self.assertTrue(res["ok"])
        self.assertEqual(res["vigencia"], "Acreditado 6 años")  # oficial, con tilde
        self.assertEqual(res["vigencia_propuesta"], "Acreditado 6 anios")  # motor, sin tilde
        self.assertEqual(
            frappe.db.get_value("Autoevaluacion", ae, "resultado_vigencia"),
            "Acreditado 6 años",
        )

    def test_finalizar_vigencia_en_proceso_si_algun_nl(self):
        """Con algún NL entre los 10 confirmados -> vigencia oficial "En proceso"."""
        arbol = factories.crear_marco_prueba(
            n_estandares=confirmacion.TOTAL_ESTANDARES, n_criterios=1, prefijo="TEST-FINNL"
        )
        ae = factories.crear_autoevaluacion(arbol, prefijo="TEST-FINNL").name
        estandares = arbol["estandares"]
        # 9 en LP + 1 en NL.
        for est in estandares[:-1]:
            factories.confirmar_estandar(ae, est, "LP", prefijo="TEST-FINNL")
        factories.confirmar_estandar(ae, estandares[-1], "NL", prefijo="TEST-FINNL")

        res = confirmacion.finalizar_vigencia(ae)

        self.assertTrue(res["ok"])
        self.assertEqual(res["vigencia"], "En proceso")
        self.assertEqual(
            frappe.db.get_value("Autoevaluacion", ae, "resultado_vigencia"),
            "En proceso",
        )

    def test_finalizar_vigencia_faltan_confirmados(self):
        """Si no están los 10 confirmados no toca la vigencia y reporta cuántos faltan."""
        # El árbol base solo tiene 3 estándares; confirmamos 2.
        factories.confirmar_estandar(self.ae, self.estandares[0], "LP", prefijo=self.PREFIJO)
        factories.confirmar_estandar(self.ae, self.estandares[1], "LP", prefijo=self.PREFIJO)

        res = confirmacion.finalizar_vigencia(self.ae)

        self.assertFalse(res["ok"])
        self.assertEqual(res["confirmados"], 2)
        self.assertEqual(res["faltan"], confirmacion.TOTAL_ESTANDARES - 2)
        # No se promovió ninguna vigencia oficial.
        self.assertIn(
            frappe.db.get_value("Autoevaluacion", self.ae, "resultado_vigencia"),
            (None, ""),
        )

    def test_finalizar_vigencia_sin_autoevaluacion_lanza(self):
        """Sin `autoevaluacion` la función corta con throw."""
        with self.assertRaises(frappe.exceptions.ValidationError):
            confirmacion.finalizar_vigencia(None)
