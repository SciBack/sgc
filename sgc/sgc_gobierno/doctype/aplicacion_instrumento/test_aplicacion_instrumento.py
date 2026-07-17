# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Suite de tests del M12 — Aplicación de Instrumento (encuestas).

El controlador (`aplicacion_instrumento.py`) aplica:
  validate() (side-effects / coherencia):
    muestra > población                     -> ValidationError
    fecha_fin < fecha_inicio                -> ValidationError
    limesurvey_response_count + base        -> deriva tasa_respuesta (acotada a 100 %)
  Validaciones INCREMENTALES por etapa (dict ORDEN):
    Planificada(0) -> En campo(1) -> Cerrada(2)
    En campo   sin fecha_inicio             -> ValidationError
    Cerrada    sin fecha_fin                -> ValidationError

Además prueba la tabulación agregada (`.tabular()` / `tabular_aplicacion`):
promedio simple, promedio ponderado por n, y desglose por dimensión.

Aplicacion Instrumento tiene Workflow (f9_workflow_encuestas): se desactiva en
setUp para poder crear la aplicación directamente en el estado que cada test
necesita, sin transicionar. Las validaciones del CONTROLADOR siguen corriendo.

Hereda de IntegrationTestCase: cada test corre en su propia transacción con
rollback automático.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc.tests import factories

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

PREF = "TESTM12A"


class IntegrationTestAplicacionInstrumento(IntegrationTestCase):
    """Validaciones por etapa + tabulación del M12 (Aplicación de Instrumento)."""

    def setUp(self):
        factories.desactivar_workflow("Aplicacion Instrumento")
        self.instrumento = factories.crear_instrumento(prefijo=PREF).name

    # -- helper de construcción --------------------------------------------
    def _apl(self, **overrides):
        return factories.crear_aplicacion_instrumento(
            instrumento=self.instrumento, prefijo=PREF, **overrides
        )

    # ======================================================================
    # Coherencia muestral y de fechas
    # ======================================================================
    def test_muestra_mayor_que_poblacion_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._apl(poblacion=100, muestra=120)

    def test_muestra_menor_que_poblacion_ok(self):
        apl = self._apl(poblacion=100, muestra=80)
        self.assertEqual(apl.muestra, 80)

    def test_fecha_fin_anterior_a_inicio_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._apl(
                fecha_inicio=nowdate(),
                fecha_fin=add_days(nowdate(), -5),
            )

    # ======================================================================
    # Derivación de la tasa de respuesta
    # ======================================================================
    def test_tasa_respuesta_se_deriva_de_muestra(self):
        # 45 respuestas sobre muestra 90 -> 50 %.
        apl = self._apl(poblacion=200, muestra=90, limesurvey_response_count=45)
        self.assertEqual(apl.tasa_respuesta, 50.0)

    def test_tasa_respuesta_cae_a_poblacion_sin_muestra(self):
        # Sin muestra, la base es la población: 30/120 -> 25 %.
        apl = self._apl(poblacion=120, limesurvey_response_count=30)
        self.assertEqual(apl.tasa_respuesta, 25.0)

    def test_tasa_respuesta_acotada_a_100(self):
        # Más respuestas que la base no supera el 100 %.
        apl = self._apl(muestra=50, limesurvey_response_count=80)
        self.assertEqual(apl.tasa_respuesta, 100.0)

    # ======================================================================
    # Validaciones incrementales por etapa
    # ======================================================================
    def test_en_campo_sin_fecha_inicio_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._apl(estado="En campo")

    def test_en_campo_con_fecha_inicio_ok(self):
        apl = self._apl(estado="En campo", fecha_inicio=nowdate())
        self.assertEqual(apl.estado, "En campo")

    def test_cerrada_sin_fecha_fin_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._apl(estado="Cerrada", fecha_inicio=nowdate())

    def test_cerrada_completa_ok(self):
        apl = self._apl(
            estado="Cerrada",
            fecha_inicio=add_days(nowdate(), -10),
            fecha_fin=nowdate(),
        )
        self.assertEqual(apl.estado, "Cerrada")

    # ======================================================================
    # Tabulación agregada
    # ======================================================================
    def test_tabular_aplicacion_vacia(self):
        apl = self._apl()
        res = apl.tabular()
        self.assertEqual(res["n_resultados"], 0)
        self.assertEqual(res["n_total"], 0)
        self.assertIsNone(res["promedio"])
        self.assertIsNone(res["promedio_ponderado"])
        self.assertEqual(res["dimensiones"], [])

    def test_tabular_promedios_simple_y_ponderado(self):
        apl = self._apl()
        # Dos dimensiones con distinto n para diferenciar simple vs ponderado.
        factories.crear_resultado_instrumento(
            apl, dimension="Trato", valor=4.0, unidad="media Likert", n=10, prefijo=PREF
        )
        factories.crear_resultado_instrumento(
            apl, dimension="Infraestructura", valor=2.0, unidad="media Likert", n=30, prefijo=PREF
        )
        res = apl.tabular()
        self.assertEqual(res["n_resultados"], 2)
        self.assertEqual(res["n_total"], 40)
        # Simple: (4 + 2) / 2 = 3.0
        self.assertEqual(res["promedio"], 3.0)
        # Ponderado: (4*10 + 2*30) / 40 = 100/40 = 2.5
        self.assertEqual(res["promedio_ponderado"], 2.5)
        self.assertEqual(len(res["dimensiones"]), 2)

    def test_tabular_desglose_por_dimension(self):
        apl = self._apl()
        # Dos filas de la MISMA dimensión: se agregan juntas.
        factories.crear_resultado_instrumento(
            apl, dimension="Trato", valor=5.0, unidad="%", n=20, prefijo=PREF
        )
        factories.crear_resultado_instrumento(
            apl, dimension="Trato", valor=3.0, unidad="%", n=20, prefijo=PREF
        )
        factories.crear_resultado_instrumento(
            apl, dimension="Aulas", valor=4.0, unidad="%", n=10, prefijo=PREF
        )
        res = apl.tabular()
        self.assertEqual(res["n_total"], 50)
        dims = {d["dimension"]: d for d in res["dimensiones"]}
        # "Aulas" ordena antes que "Trato".
        self.assertEqual([d["dimension"] for d in res["dimensiones"]], ["Aulas", "Trato"])
        trato = dims["Trato"]
        self.assertEqual(trato["n_resultados"], 2)
        self.assertEqual(trato["n"], 40)
        self.assertEqual(trato["promedio"], 4.0)           # (5+3)/2
        self.assertEqual(trato["promedio_ponderado"], 4.0)  # (5*20+3*20)/40
        self.assertEqual(trato["pct_muestra"], 80.0)        # 40/50
        self.assertEqual(trato["unidad"], "%")

    def test_tabular_aplicacion_inexistente_falla(self):
        from sgc.sgc_gobierno.doctype.resultado_instrumento.resultado_instrumento import (
            tabular_aplicacion,
        )

        with self.assertRaises(frappe.ValidationError):
            tabular_aplicacion("APL-9999-99999")
