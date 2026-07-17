# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.tablero_ejecutivo` — M13, vista institucional de acreditación.

Verifica que `resumen_ejecutivo`:
- Devuelve la estructura esperada (cobertura, programas, niveles, cbc, mejora).
- Cuenta la cobertura contra el total de Programa Sede.
- Clasifica los estándares por nivel: usa el OFICIAL cuando está confirmado y el
  propuesto por el motor cuando no; lo no valorado cae en `sin_valorar`.
"""

import frappe
from frappe.tests import IntegrationTestCase

from sgc.tablero_ejecutivo import resumen_ejecutivo
from sgc.tests import factories


class IntegrationTestTableroEjecutivo(IntegrationTestCase):
    def test_estructura(self):
        """El payload trae las 5 secciones y los conteos son enteros."""
        r = resumen_ejecutivo()
        self.assertEqual(set(r.keys()), {"cobertura", "programas", "niveles", "cbc", "mejora"})
        self.assertIsInstance(r["programas"], list)
        for clave in ("NL", "L", "LP", "sin_valorar"):
            self.assertIsInstance(r["niveles"][clave], int)
        self.assertIsInstance(r["cobertura"]["programas_total"], int)
        self.assertIsInstance(r["mejora"]["nc_abiertas"], int)

    def test_cobertura_cuenta_autoevaluaciones_vivas(self):
        """Crear una autoevaluación viva incrementa la cobertura."""
        base = resumen_ejecutivo()["cobertura"]["con_autoevaluacion"]
        arbol = factories.crear_marco_prueba(n_estandares=2, n_criterios=1, prefijo="TEST-EJEC")
        factories.crear_autoevaluacion(arbol, prefijo="TEST-EJEC")
        self.assertEqual(resumen_ejecutivo()["cobertura"]["con_autoevaluacion"], base + 1)

    def test_nivel_propuesto_se_clasifica(self):
        """Un estándar con nivel propuesto (sin confirmar) cuenta en su sigla."""
        arbol = factories.crear_marco_prueba(n_estandares=1, n_criterios=2, prefijo="TEST-EJEC2")
        ae = factories.crear_autoevaluacion(arbol, prefijo="TEST-EJEC2")
        est = arbol["estandares"][0]
        # Valorar ambos criterios como Cumple -> el motor propone LP.
        factories.valorar_estandar(ae, arbol["criterios"][est], default=factories.CUMPLE)

        info = next(p for p in resumen_ejecutivo()["programas"] if p["name"] == ae.name)
        self.assertEqual(info["estandares_total"], 1)
        self.assertEqual(info["niveles"]["LP"], 1)

    def test_nivel_oficial_confirmado_prevalece(self):
        """Con el nivel oficial confirmado, se clasifica por ese (no por el propuesto)."""
        arbol = factories.crear_marco_prueba(n_estandares=1, n_criterios=2, prefijo="TEST-EJEC3")
        ae = factories.crear_autoevaluacion(arbol, prefijo="TEST-EJEC3")
        est = arbol["estandares"][0]
        factories.valorar_estandar(ae, arbol["criterios"][est], default=factories.CUMPLE)  # propone LP
        factories.confirmar_estandar(ae, est, "L", prefijo="TEST-EJEC3")  # oficial: L

        info = next(p for p in resumen_ejecutivo()["programas"] if p["name"] == ae.name)
        self.assertEqual(info["niveles"]["L"], 1)
        self.assertEqual(info["niveles"]["LP"], 0)
