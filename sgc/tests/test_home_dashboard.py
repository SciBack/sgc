# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.home_dashboard` — panel operativo de Inicio.

Verifica que `resumen_inicio`:
- Devuelve la estructura esperada (autoevaluacion, pendientes, horizonte_dias).
- Trae las 6 tarjetas de pendientes con conteos enteros y su tono.
- Refleja la autoevaluación activa con el conteo de criterios valorados/pendientes.
"""

import frappe
from frappe.tests import IntegrationTestCase

from sgc.home_dashboard import resumen_inicio
from sgc.tests import factories

_CLAVES = {
    "evidencias_vencidas",
    "evidencias_por_vencer",
    "nc_abiertas",
    "planes_riesgo",
    "acciones_por_vencer",
    "docs_por_revisar",
}


class IntegrationTestHomeDashboard(IntegrationTestCase):
    def test_estructura_y_pendientes(self):
        """El payload trae las claves esperadas y las 6 tarjetas de pendientes."""
        r = resumen_inicio()
        self.assertEqual(
            set(r.keys()), {"autoevaluaciones", "programas_total", "pendientes", "horizonte_dias"}
        )
        self.assertIsInstance(r["autoevaluaciones"], list)
        self.assertIsInstance(r["programas_total"], int)
        claves = {p["clave"] for p in r["pendientes"]}
        self.assertEqual(claves, _CLAVES)
        for p in r["pendientes"]:
            self.assertIsInstance(p["valor"], int)
            self.assertIn(p["tono"], ("rojo", "ambar"))

    def test_evidencia_vencida_se_cuenta(self):
        """Una Evidencia en estado 'Vencida' incrementa la tarjeta de vencidas."""
        base = next(p["valor"] for p in resumen_inicio()["pendientes"] if p["clave"] == "evidencias_vencidas")
        ev = factories.crear_evidencia()
        frappe.db.set_value("Evidencia", ev.name, "estado", "Vencida")
        despues = next(p["valor"] for p in resumen_inicio()["pendientes"] if p["clave"] == "evidencias_vencidas")
        self.assertEqual(despues, base + 1)

    def test_autoevaluacion_en_la_lista_con_criterios(self):
        """Una Autoevaluacion viva aparece en la lista con total/valorados/pendientes."""
        arbol = factories.crear_marco_prueba(n_estandares=2, n_criterios=3, prefijo="TEST-HOME")
        ae = factories.crear_autoevaluacion(arbol, prefijo="TEST-HOME")
        # Valorar un criterio del primer estándar.
        est = arbol["estandares"][0]
        factories.valorar_criterio(ae, arbol["criterios"][est][0])

        info = next((a for a in resumen_inicio()["autoevaluaciones"] if a["name"] == ae.name), None)
        self.assertIsNotNone(info)
        # 2 estándares x 3 criterios = 6 criterios valorables en el marco.
        self.assertEqual(info["criterios_total"], 6)
        self.assertGreaterEqual(info["criterios_valorados"], 1)
        self.assertEqual(
            info["criterios_pendientes"], info["criterios_total"] - info["criterios_valorados"]
        )
