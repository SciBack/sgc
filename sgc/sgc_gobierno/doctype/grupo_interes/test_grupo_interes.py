# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Suite de tests del M12 — Grupo de Interés.

Verifica el controlador (`grupo_interes.py`): normalización (strip) del código
y el nombre. El Grupo de Interés no tiene Workflow (sin campo `estado`).
"""
from frappe.tests import IntegrationTestCase

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

PREF = "TESTM12G"


class IntegrationTestGrupoInteres(IntegrationTestCase):
    """Validaciones del Grupo de Interés (M12)."""

    def test_codigo_y_nombre_se_normalizan(self):
        gi = factories.crear_grupo_interes(
            codigo=f"{PREF}-STRIP ", nombre="  Egresados  ", prefijo=PREF
        )
        self.assertEqual(gi.codigo, f"{PREF}-STRIP")
        self.assertEqual(gi.nombre, "Egresados")

    def test_tipos_validos(self):
        for tipo in ("Beneficiario", "Colaborador", "Externo"):
            gi = factories.crear_grupo_interes(tipo=tipo, prefijo=PREF)
            self.assertEqual(gi.tipo, tipo)
