# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Suite de Evaluacion Riesgo — el cálculo que nunca existió.

Recorrido del flujo 13 en producción (2026-08-23): `score` y `nivel` estaban
declarados como "calculado en F4 (Server Script)" y ese script no existía, así
que toda evaluación nacía con score 0 y nivel «Bajo» (la primera opción del
Select, que Frappe rellena sola). Un inventario de riesgos donde todo sale
«Bajo» afirma lo contrario de lo que ISO 9001:2015 §6.1 pide determinar.

Se verifica el cálculo por los dos caminos de escala (umbrales explícitos de la
`Matriz Riesgo` y reparto proporcional cuando no los hay), que una escala
ilegible no tumbe el guardado, y que la firma `evaluado_por` la ponga el
servidor y no quien teclea.
"""
import json

import frappe
from frappe.tests import IntegrationTestCase

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

UMBRALES_5x5 = [
    {"min": 1, "max": 4, "nivel": "Bajo"},
    {"min": 5, "max": 9, "nivel": "Moderado"},
    {"min": 10, "max": 16, "nivel": "Alto"},
    {"min": 17, "max": 25, "nivel": "Extremo"},
]


class IntegrationTestEvaluacionRiesgo(IntegrationTestCase):
    def setUp(self):
        factories.desactivar_workflow("Riesgo")

    # -- helpers ------------------------------------------------------------
    def _matriz(self, codigo, **overrides):
        vals = {
            "doctype": "Matriz Riesgo",
            "codigo": codigo,
            "nombre": f"Matriz {codigo}",
            "dimension": 5,
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _riesgo(self, matriz=None):
        doc = frappe.get_doc({
            "doctype": "Riesgo",
            "titulo": "Riesgo para evaluar",
            "categoria": "Operacional",
            "matriz_riesgo": matriz.name if matriz else None,
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _evaluar(self, riesgo, probabilidad, impacto, **overrides):
        vals = {
            "doctype": "Evaluacion Riesgo",
            "riesgo": riesgo.name,
            "momento": "Inherente",
            "fecha": frappe.utils.nowdate(),
            "probabilidad": probabilidad,
            "impacto": impacto,
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    # ======================================================================
    # score = probabilidad x impacto
    # ======================================================================
    def test_score_es_probabilidad_por_impacto(self):
        r = self._riesgo()
        self.assertEqual(self._evaluar(r, 4, 5).score, 20)

    def test_evaluacion_sin_valores_no_se_guarda(self):
        r = self._riesgo()
        with self.assertRaises(frappe.ValidationError):
            self._evaluar(r, 0, 3)

    # ======================================================================
    # nivel: umbrales de la matriz, proporcional, o en blanco
    # ======================================================================
    def test_nivel_por_umbrales_de_la_matriz(self):
        m = self._matriz("TEST-MTX-UMB", umbrales=json.dumps(UMBRALES_5x5))
        r = self._riesgo(m)
        self.assertEqual(self._evaluar(r, 1, 1).nivel, "Bajo")
        self.assertEqual(self._evaluar(r, 2, 3).nivel, "Moderado")
        self.assertEqual(self._evaluar(r, 4, 3).nivel, "Alto")
        self.assertEqual(self._evaluar(r, 5, 5).nivel, "Extremo")

    def test_nivel_proporcional_sin_umbrales(self):
        """Sin umbrales, el rango 1..dimensión² se reparte en cuatro tramos."""
        m = self._matriz("TEST-MTX-DIM")
        r = self._riesgo(m)
        self.assertEqual(self._evaluar(r, 1, 1).nivel, "Bajo")       # 1/25
        self.assertEqual(self._evaluar(r, 4, 3).nivel, "Moderado")   # 12/25
        self.assertEqual(self._evaluar(r, 5, 5).nivel, "Extremo")    # 25/25

    def test_escala_ilegible_no_rompe_el_guardado(self):
        """Un `umbrales` mal escrito degrada al reparto proporcional, no revienta."""
        m = self._matriz("TEST-MTX-MAL", umbrales='{"esto": "no es una lista"}')
        r = self._riesgo(m)
        e = self._evaluar(r, 5, 5)
        self.assertEqual(e.score, 25)
        self.assertEqual(e.nivel, "Extremo")

    def test_sin_matriz_el_nivel_queda_en_blanco(self):
        """Sin criterios de riesgo no hay valoración (ISO 31000 §6.4.4).

        Es el fallo original al revés: antes mentía con «Bajo»; ahora dice que no
        lo sabe.
        """
        r = self._riesgo()
        e = self._evaluar(r, 5, 5)
        self.assertEqual(e.score, 25)
        self.assertFalse(e.nivel)

    # ======================================================================
    # Firma de quien evalúa
    # ======================================================================
    def test_evaluado_por_lo_sella_el_servidor(self):
        r = self._riesgo()
        e = self._evaluar(r, 3, 3, evaluado_por="Administrator")
        self.assertEqual(e.evaluado_por, frappe.session.user)

    def test_reevaluar_resella_la_firma(self):
        r = self._riesgo()
        e = self._evaluar(r, 3, 3)
        frappe.db.set_value("Evaluacion Riesgo", e.name, "evaluado_por", "Administrator")
        e.reload()
        e.impacto = 5
        e.save(ignore_permissions=True)
        self.assertEqual(e.evaluado_por, frappe.session.user)
        self.assertEqual(e.score, 15)
