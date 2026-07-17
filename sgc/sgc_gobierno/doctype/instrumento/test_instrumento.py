# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Suite de tests del M12 — Instrumento.

Verifica el controlador (`instrumento.py`):
  validate():
    plataforma "Otra" con survey_id       -> se descarta el survey_id
    plataforma "LimeSurvey" con survey_id  -> se conserva
    código / nombre                        -> se normalizan (strip)
El Instrumento no tiene Workflow (sin campo `estado`), así que no requiere
desactivación de workflow.
"""
from frappe.tests import IntegrationTestCase

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

PREF = "TESTM12I"


class IntegrationTestInstrumento(IntegrationTestCase):
    """Validaciones del Instrumento (M12)."""

    def test_otra_plataforma_descarta_survey_id(self):
        ins = factories.crear_instrumento(
            plataforma="Otra", limesurvey_survey_id="12345", prefijo=PREF
        )
        self.assertFalse(ins.limesurvey_survey_id)

    def test_limesurvey_conserva_survey_id(self):
        ins = factories.crear_instrumento(
            plataforma="LimeSurvey", limesurvey_survey_id="98765", prefijo=PREF
        )
        self.assertEqual(ins.limesurvey_survey_id, "98765")

    def test_codigo_y_nombre_se_normalizan(self):
        ins = factories.crear_instrumento(
            codigo=f"{PREF}-NORM ", nombre="  Encuesta X  ", prefijo=PREF
        )
        self.assertEqual(ins.codigo, f"{PREF}-NORM")
        self.assertEqual(ins.nombre, "Encuesta X")

    def test_instrumento_ligado_a_grupo_interes(self):
        gi = factories.crear_grupo_interes(tipo="Beneficiario", prefijo=PREF)
        ins = factories.crear_instrumento(grupo_interes=gi, prefijo=PREF)
        self.assertEqual(ins.grupo_interes, gi.name)
