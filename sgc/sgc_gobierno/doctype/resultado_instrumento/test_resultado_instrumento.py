# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Suite de tests del M12 — Resultado de Instrumento.

Verifica el controlador (`resultado_instrumento.py`):
  validate():
    n negativo                          -> ValidationError
    unidad "%" con valor fuera de [0,100] -> ValidationError
    fecha_corte vacía                   -> hereda fecha_fin de la aplicación (o hoy)

La aplicación padre tiene Workflow; se desactiva en setUp para poder prepararla
con fechas sin transicionar.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

PREF = "TESTM12R"


class IntegrationTestResultadoInstrumento(IntegrationTestCase):
    """Validaciones del Resultado de Instrumento (M12)."""

    def setUp(self):
        factories.desactivar_workflow("Aplicacion Instrumento")
        self.apl = factories.crear_aplicacion_instrumento(prefijo=PREF)

    def test_n_negativo_falla(self):
        with self.assertRaises(frappe.ValidationError):
            factories.crear_resultado_instrumento(
                self.apl, dimension="Trato", valor=3.0, n=-1, prefijo=PREF
            )

    def test_porcentaje_fuera_de_rango_falla(self):
        with self.assertRaises(frappe.ValidationError):
            factories.crear_resultado_instrumento(
                self.apl, dimension="Satisfacción", valor=150.0, unidad="%", n=10, prefijo=PREF
            )

    def test_porcentaje_en_rango_ok(self):
        res = factories.crear_resultado_instrumento(
            self.apl, dimension="Satisfacción", valor=87.5, unidad="%", n=10, prefijo=PREF
        )
        self.assertEqual(res.valor, 87.5)

    def test_fecha_corte_hereda_fecha_fin_de_aplicacion(self):
        fin = nowdate()
        self.apl.fecha_inicio = add_days(fin, -10)
        self.apl.fecha_fin = fin
        self.apl.flags.ignore_permissions = True
        self.apl.save(ignore_permissions=True)
        res = factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=4.0, n=5, prefijo=PREF
        )
        self.assertEqual(str(res.fecha_corte), fin)

    def test_fecha_corte_explicita_se_respeta(self):
        corte = add_days(nowdate(), -3)
        res = factories.crear_resultado_instrumento(
            self.apl, dimension="Trato", valor=4.0, n=5, fecha_corte=corte, prefijo=PREF
        )
        self.assertEqual(str(res.fecha_corte), corte)
