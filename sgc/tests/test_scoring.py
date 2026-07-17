# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Suite de REFERENCIA para `sgc/scoring.py` — el motor NL/L/LP + vigencia + avance.

Es la plantilla que siguen los demás test del SGC:
  - hereda de `frappe.tests.IntegrationTestCase` (cada test corre en su propia
    transacción con rollback automático);
  - `setUp` construye el dato base con las factories de `sgc.tests.factories`;
  - cada test ejercita UNA regla del contrato F2 con asserts reales.

Reglas verificadas (scoring.py):
  proponer_nivel_estandar:
    todos "Cumple"           -> "LP"
    algún "No cumple"        -> "NL"      (precede a L y LP)
    algún "Cumple parcial"   -> "L"
    algún criterio sin valor -> None      (incompleto)
    algún "No aplica"        -> None      (incompleto; y para AVANCE tampoco cuenta)
  _calcular_avance_pct:
    denominador = criterios VALORABLES del marco (tipo=Criterio, es_valorable=1);
      EXCLUYE los estándares (que también llevan es_valorable=1 en CONEAU).
    numerador   = criterios con juicio real (Cumple / Cumple parcial / No cumple);
      "No aplica" y vacío NO cuentan -> con criterios sin valorar nunca llega a 100 %.
  proponer_vigencia (sobre los 'nivel' CONFIRMADOS):
    faltan confirmados       -> None
    algún NL                 -> "En proceso"
    todos LP                 -> "Acreditado 6 anios"
    combo L/LP (sin NL)      -> "Acreditado 3 anios"
    (El "Acreditado 8 anios" NO lo produce este motor: es Tabla 10 / F6.)
  _upsert_valoracion_estandar:
    auto-sana duplicados del par (autoevaluacion, elemento_marco): conserva el
    más antiguo (donde vive el 'nivel' confirmado) y borra los extras.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc import scoring
from sgc.tests import factories


class IntegrationTestScoring(IntegrationTestCase):
    """Motor de scoring de la autoevaluación (Sección IX del Modelo CONEAU)."""

    def setUp(self):
        # Árbol base: marco con 3 estándares × 3 criterios + escala NL/L/LP.
        self.arbol = factories.crear_marco_prueba(n_estandares=3, n_criterios=3)
        self.marco = self.arbol["marco"]
        self.estandares = self.arbol["estandares"]          # ["TEST-E1", "TEST-E2", "TEST-E3"]
        self.criterios = self.arbol["criterios"]            # {est: [criterios]}
        self.ae = factories.crear_autoevaluacion(self.marco).name

    # -- helpers de lectura -------------------------------------------------
    def _nivel_propuesto(self, estandar):
        return frappe.db.get_value(
            "Valoracion Estandar",
            {"autoevaluacion": self.ae, "elemento_marco": estandar},
            "nivel_propuesto",
        )

    def _valoraciones_estandar(self, estandar):
        return frappe.get_all(
            "Valoracion Estandar",
            filters={"autoevaluacion": self.ae, "elemento_marco": estandar},
            pluck="name",
            order_by="creation asc",
        )

    # ======================================================================
    # proponer_nivel_estandar — la regla por estándar
    # ======================================================================
    def test_nivel_lp_cuando_todos_cumplen(self):
        est = self.estandares[0]
        factories.valorar_estandar(self.ae, self.criterios[est], default=factories.CUMPLE)
        self.assertEqual(scoring.proponer_nivel_estandar(self.ae, est), "LP")
        # y quedó persistido en la Valoracion Estandar
        self.assertEqual(self._nivel_propuesto(est), "LP")

    def test_nivel_nl_cuando_algun_no_cumple(self):
        est = self.estandares[0]
        # un "No cumple", el resto "Cumple"
        factories.valorar_estandar(self.ae, self.criterios[est], juicios={0: factories.NO_CUMPLE})
        self.assertEqual(scoring.proponer_nivel_estandar(self.ae, est), "NL")

    def test_nivel_l_cuando_algun_cumple_parcial(self):
        est = self.estandares[0]
        factories.valorar_estandar(self.ae, self.criterios[est], juicios={1: factories.CUMPLE_PARCIAL})
        self.assertEqual(scoring.proponer_nivel_estandar(self.ae, est), "L")

    def test_nivel_none_cuando_criterio_sin_valorar(self):
        est = self.estandares[0]
        # valorar solo 2 de 3 criterios -> incompleto
        crits = self.criterios[est]
        factories.valorar_criterio(self.ae, crits[0], factories.CUMPLE)
        factories.valorar_criterio(self.ae, crits[1], factories.CUMPLE)
        self.assertIsNone(scoring.proponer_nivel_estandar(self.ae, est))
        # persistió vacío (no "None")
        self.assertIn(self._nivel_propuesto(est), (None, ""))

    def test_precedencia_no_cumple_sobre_parcial(self):
        # NL se evalúa antes que L: un No cumple + un Cumple parcial -> NL.
        est = self.estandares[0]
        factories.valorar_estandar(
            self.ae, self.criterios[est],
            juicios={0: factories.NO_CUMPLE, 1: factories.CUMPLE_PARCIAL},
        )
        self.assertEqual(scoring.proponer_nivel_estandar(self.ae, est), "NL")

    def test_no_aplica_deja_el_estandar_incompleto(self):
        # "No aplica" NO fija nivel: se trata como sin valorar -> propuesto None,
        # aunque para el AVANCE sí cuente (ver test de avance).
        est = self.estandares[0]
        factories.valorar_estandar(
            self.ae, self.criterios[est], juicios={2: factories.NO_APLICA},
        )
        self.assertIsNone(scoring.proponer_nivel_estandar(self.ae, est))

    def test_estandar_sin_criterios_es_none(self):
        # Un estándar sin criterios valorables -> None (no hay base para proponer).
        arbol = factories.crear_marco_prueba(n_estandares=1, n_criterios=0, prefijo="TESTVAC")
        ae2 = factories.crear_autoevaluacion(arbol, prefijo="TESTVAC").name
        est_vacio = arbol["estandares"][0]
        self.assertIsNone(scoring.proponer_nivel_estandar(ae2, est_vacio))

    # ======================================================================
    # _calcular_avance_pct — juicio real / criterios valorables (sin estándares)
    # ======================================================================
    def test_avance_cero_sin_valoraciones(self):
        self.assertEqual(scoring._calcular_avance_pct(self.ae), 0.0)

    def test_avance_parcial(self):
        # marco 2×2 = 4 criterios; valorar 2 -> 50 %.
        arbol = factories.crear_marco_prueba(n_estandares=2, n_criterios=2, prefijo="TESTAV")
        ae = factories.crear_autoevaluacion(arbol, prefijo="TESTAV").name
        e1 = arbol["estandares"][0]
        factories.valorar_estandar(ae, arbol["criterios"][e1], default=factories.CUMPLE)
        self.assertEqual(scoring._calcular_avance_pct(ae), 50.0)

    def test_avance_criterio_sin_valorar_no_llega_a_100(self):
        # marco 2×2 = 4 criterios; valorar solo 3 -> 75 %, nunca 100 %.
        arbol = factories.crear_marco_prueba(n_estandares=2, n_criterios=2, prefijo="TESTSV")
        ae = factories.crear_autoevaluacion(arbol, prefijo="TESTSV").name
        e1, e2 = arbol["estandares"]
        factories.valorar_estandar(ae, arbol["criterios"][e1], default=factories.CUMPLE)
        factories.valorar_criterio(ae, arbol["criterios"][e2][0], factories.CUMPLE)
        # el 4º criterio queda sin tocar
        self.assertEqual(scoring._calcular_avance_pct(ae), 75.0)

    def test_avance_no_aplica_no_cuenta_y_no_llega_a_100(self):
        # 4 criterios; uno en "No aplica" -> solo 3 con juicio real -> 75 %, no 100 %.
        # (Antes "No aplica" contaba como valorado y daba 100 % — el porcentaje mentía.)
        arbol = factories.crear_marco_prueba(n_estandares=2, n_criterios=2, prefijo="TESTNA")
        ae = factories.crear_autoevaluacion(arbol, prefijo="TESTNA").name
        e1, e2 = arbol["estandares"]
        factories.valorar_estandar(ae, arbol["criterios"][e1], default=factories.CUMPLE)
        factories.valorar_estandar(
            ae, arbol["criterios"][e2], juicios={0: factories.NO_APLICA}, default=factories.CUMPLE,
        )
        res = scoring.proponer_vigencia(ae)
        # "No aplica" NO cuenta como valorado -> 3/4 = 75 %, coherente con el nivel.
        self.assertEqual(res["avance_pct"], 75.0)
        # y ese estándar con "No aplica" también queda incompleto para el nivel.
        self.assertIsNone(scoring.proponer_nivel_estandar(ae, e2))

    def test_avance_excluye_estandares_valorables_del_denominador(self):
        # Reproduce el bug real de prod: el marco CONEAU marca es_valorable=1
        # también en los estándares. El denominador del avance debe seguir siendo
        # SOLO los criterios (tipo=Criterio); si contara los estándares, 4 criterios
        # valorados sobre 6 "valorables" daría 66 % en vez del 100 % correcto.
        arbol = factories.crear_marco_prueba(n_estandares=2, n_criterios=2, prefijo="TESTEV")
        ae = factories.crear_autoevaluacion(arbol, prefijo="TESTEV").name
        # Marcar los estándares como es_valorable=1 (como en el marco CONEAU real).
        for est in arbol["estandares"]:
            frappe.db.set_value("Elemento Marco", est, "es_valorable", 1)
        # El denominador de criterios valorables NO incluye los 2 estándares.
        self.assertEqual(len(scoring._criterios_valorables_del_marco(arbol["marco"])), 4)
        # Valorar los 4 criterios -> 100 % (no 4/6 = 66.67 %).
        for est in arbol["estandares"]:
            factories.valorar_estandar(ae, arbol["criterios"][est], default=factories.CUMPLE)
        self.assertEqual(scoring._calcular_avance_pct(ae), 100.0)

    # ======================================================================
    # proponer_vigencia — sobre los niveles CONFIRMADOS (Tabla 9)
    # ======================================================================
    def test_vigencia_none_si_no_estan_todos_confirmados(self):
        # confirmar solo 2 de 3 -> incompleto -> None.
        factories.confirmar_estandar(self.ae, self.estandares[0], "LP")
        factories.confirmar_estandar(self.ae, self.estandares[1], "LP")
        res = scoring.proponer_vigencia(self.ae)
        self.assertIsNone(res["vigencia_propuesta"])
        # y se persiste vacío en la Autoevaluacion
        self.assertIn(
            frappe.db.get_value("Autoevaluacion", self.ae, "vigencia_propuesta"),
            (None, ""),
        )

    def test_vigencia_6_anios_todos_lp(self):
        for est in self.estandares:
            factories.confirmar_estandar(self.ae, est, "LP")
        self.assertEqual(scoring.proponer_vigencia(self.ae)["vigencia_propuesta"],
                         "Acreditado 6 anios")

    def test_vigencia_3_anios_combo_l_lp_sin_nl(self):
        factories.confirmar_estandar(self.ae, self.estandares[0], "L")
        factories.confirmar_estandar(self.ae, self.estandares[1], "LP")
        factories.confirmar_estandar(self.ae, self.estandares[2], "L")
        self.assertEqual(scoring.proponer_vigencia(self.ae)["vigencia_propuesta"],
                         "Acreditado 3 anios")

    def test_vigencia_en_proceso_si_algun_nl(self):
        factories.confirmar_estandar(self.ae, self.estandares[0], "LP")
        factories.confirmar_estandar(self.ae, self.estandares[1], "NL")
        factories.confirmar_estandar(self.ae, self.estandares[2], "L")
        self.assertEqual(scoring.proponer_vigencia(self.ae)["vigencia_propuesta"],
                         "En proceso")

    # ======================================================================
    # _upsert_valoracion_estandar — auto-saneo de duplicados
    # ======================================================================
    def test_upsert_dedup_conserva_la_mas_antigua(self):
        est = self.estandares[0]
        # Dos filas duplicadas del mismo par. La ANTIGUA lleva el `nivel` oficial.
        ve_antigua = factories.crear_valoracion_estandar(
            self.ae, est, nivel_sigla="LP", confirmado=1,
        )
        # Garantizar que 'antigua' sea estrictamente la más vieja (creation asc).
        frappe.db.set_value(
            "Valoracion Estandar", ve_antigua.name, "creation",
            "2020-01-01 00:00:00", update_modified=False,
        )
        ve_extra = factories.crear_valoracion_estandar(
            self.ae, est, nivel_propuesto="NL",
        )
        # Precondición: hay 2 filas.
        self.assertEqual(len(self._valoraciones_estandar(est)), 2)

        # Valorar todos "Cumple" dispara el motor -> _upsert dedupa y recomputa.
        factories.valorar_estandar(self.ae, self.criterios[est], default=factories.CUMPLE)

        restantes = self._valoraciones_estandar(est)
        self.assertEqual(len(restantes), 1)                      # se colapsó a 1
        self.assertEqual(restantes[0], ve_antigua.name)          # conservó la más antigua
        self.assertFalse(frappe.db.exists("Valoracion Estandar", ve_extra.name))

        superviviente = frappe.get_doc("Valoracion Estandar", ve_antigua.name)
        self.assertEqual(superviviente.nivel_propuesto, "LP")    # recomputó el propuesto
        # el `nivel` oficial confirmado se preservó (el motor nunca lo toca)
        self.assertEqual(superviviente.nivel, factories.nivel_escala_por_sigla("LP"))
        self.assertEqual(superviviente.confirmado, 1)

    # ======================================================================
    # recalcular_autoevaluacion — integración de la cadena completa
    # ======================================================================
    def test_recalcular_autoevaluacion_integra_niveles_y_avance(self):
        # E1 todos Cumple -> LP ; E2 un No cumple -> NL ; E3 un parcial -> L.
        e1, e2, e3 = self.estandares
        factories.valorar_estandar(self.ae, self.criterios[e1], default=factories.CUMPLE)
        factories.valorar_estandar(self.ae, self.criterios[e2], juicios={0: factories.NO_CUMPLE})
        factories.valorar_estandar(self.ae, self.criterios[e3], juicios={0: factories.CUMPLE_PARCIAL})

        res = scoring.recalcular_autoevaluacion(self.ae)

        self.assertEqual(res["estandares"][e1], "LP")
        self.assertEqual(res["estandares"][e2], "NL")
        self.assertEqual(res["estandares"][e3], "L")
        # todos los criterios valorados -> avance 100 %
        self.assertEqual(res["avance_pct"], 100.0)
        # sin confirmar los niveles oficiales, la vigencia sigue incompleta
        self.assertIsNone(res["vigencia_propuesta"])
