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
from frappe.model.workflow import apply_workflow
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

    # ======================================================================
    # Seam manual de publicación (fuera de la transición)
    # ======================================================================
    def test_publicar_indicadores_exige_estado_cerrada(self):
        apl = self._apl(estado="En campo", fecha_inicio=nowdate())
        with self.assertRaises(frappe.ValidationError):
            apl.publicar_indicadores()


# ==========================================================================
# Puente Encuestas -> Indicadores disparado por el CIERRE real del workflow
# ==========================================================================
# Acciones del Workflow "Aplicacion Instrumento SGC" en orden hasta "Cerrada"
# (ver sgc/setup/f9_workflow_encuestas.py WF_APLICACION["transitions"]).
_CADENA_CIERRE = ("Iniciar campo", "Cerrar aplicacion")


class IntegrationTestCierreAplicacionPublicaIndicadores(IntegrationTestCase):
    """El cierre por Workflow materializa los `Valor Indicador` (A2).

    NO se llama `factories.desactivar_workflow`: se necesita el Workflow ACTIVO
    porque el disparo real es `apply_workflow` -> `doc.save()` -> `on_update`.
    Reasignar `estado` a mano y guardar NO es el camino a probar (gotcha
    conocido del repo).
    """

    def setUp(self):
        self.instrumento = factories.crear_instrumento(prefijo=PREF).name

    def _indicador(self):
        """Indicador mínimo (solo codigo+nombre son reqd). Creado inline: la
        factory compartida `sgc/tests/factories.py` está fuera de alcance."""
        codigo = f"{PREF}-IND-{frappe.generate_hash(length=8)}"
        doc = frappe.get_doc({
            "doctype": "Indicador",
            "codigo": codigo,
            "nombre": f"Satisfacción de prueba {codigo}",
            "categoria": "Satisfaccion",
        })
        doc.insert(ignore_permissions=True)
        return doc.name

    def _cerrar(self, apl):
        """Recorre la cadena REAL de transiciones hasta 'Cerrada'."""
        doc = frappe.get_doc("Aplicacion Instrumento", apl.name)
        for accion in _CADENA_CIERRE:
            doc = apply_workflow(doc, accion)
        doc.reload()
        return doc

    def test_cerrar_publica_el_valor_indicador(self):
        ind = self._indicador()
        apl = factories.crear_aplicacion_instrumento(
            instrumento=self.instrumento,
            prefijo=PREF,
            fecha_inicio=add_days(nowdate(), -10),
            fecha_fin=nowdate(),
        )
        res = factories.crear_resultado_instrumento(
            apl, dimension="Trato", valor=4.0, n=10, indicador=ind, prefijo=PREF
        )

        # Antes de cerrar no existe nada publicado.
        self.assertEqual(frappe.db.count("Valor Indicador", {"indicador": ind}), 0)

        cerrada = self._cerrar(apl)
        self.assertEqual(cerrada.estado, "Cerrada")

        vi = frappe.db.get_value(
            "Resultado Instrumento", res.name, "valor_indicador"
        )
        self.assertTrue(vi, "el cierre debe escribir el back-link valor_indicador")
        doc_vi = frappe.get_doc("Valor Indicador", vi)
        self.assertEqual(doc_vi.indicador, ind)
        self.assertEqual(doc_vi.valor_num, 4.0)
        self.assertEqual(doc_vi.fuente, "encuesta")
        self.assertEqual(doc_vi.calculado, 1)

    def test_cerrar_sin_indicador_declarado_no_publica(self):
        """Sin enlace explícito el cierre no rompe: simplemente no publica."""
        apl = factories.crear_aplicacion_instrumento(
            instrumento=self.instrumento,
            prefijo=PREF,
            fecha_inicio=add_days(nowdate(), -10),
            fecha_fin=nowdate(),
        )
        res = factories.crear_resultado_instrumento(
            apl, dimension="Satisfacción general", valor=4.0, n=10, prefijo=PREF
        )
        cerrada = self._cerrar(apl)
        self.assertEqual(cerrada.estado, "Cerrada")
        self.assertFalse(
            frappe.db.get_value("Resultado Instrumento", res.name, "valor_indicador")
        )

    def test_republicar_tras_el_cierre_no_duplica(self):
        """Resultados cargados DESPUÉS del cierre se incorporan al re-publicar,
        sobre el MISMO Valor Indicador."""
        ind = self._indicador()
        apl = factories.crear_aplicacion_instrumento(
            instrumento=self.instrumento,
            prefijo=PREF,
            fecha_inicio=add_days(nowdate(), -10),
            fecha_fin=nowdate(),
        )
        factories.crear_resultado_instrumento(
            apl, dimension="Trato", valor=4.0, n=10, indicador=ind, prefijo=PREF
        )
        cerrada = self._cerrar(apl)
        vi_inicial = cerrada.publicar_indicadores()["publicados"][0]["valor_indicador"]

        # Llega un resultado tardío que baja el promedio ponderado.
        factories.crear_resultado_instrumento(
            apl, dimension="Aulas", valor=2.0, n=30, indicador=ind, prefijo=PREF
        )
        res = cerrada.publicar_indicadores()

        self.assertEqual(res["publicados"][0]["valor_indicador"], vi_inicial)
        self.assertEqual(res["publicados"][0]["valor_num"], 2.5)  # (4*10+2*30)/40
        self.assertEqual(frappe.db.count("Valor Indicador", {"indicador": ind}), 1)
