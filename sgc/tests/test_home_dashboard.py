# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.home_dashboard` — panel operativo de Inicio.

Verifica que `resumen_inicio`:
- Devuelve la estructura esperada (autoevaluacion, pendientes, horizonte_dias).
- Trae las 8 tarjetas de pendientes con conteos enteros y su tono.
- Refleja la autoevaluación activa con el conteo de criterios valorados/pendientes.
- GRC: cuenta riesgos críticos (nivel resuelto por `Evaluacion Riesgo`) y
  hallazgos de auditoría abiertos.

Los riesgos/hallazgos se crean con helpers PRIVADOS locales: `factories.py` es
archivo compartido y no se toca en esta etapa. Todo se mide por delta (producción
ya tiene datos: la base no es 0).
"""

import itertools

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
    "riesgos_criticos",
    "hallazgos_abiertos",
    "docs_por_revisar",
}

_seq = itertools.count(1)


def _insertar(doctype, valores):
    doc = frappe.get_doc({"doctype": doctype, **valores})
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    return doc


def _valor(payload, clave):
    return next(p["valor"] for p in payload["pendientes"] if p["clave"] == clave)


class IntegrationTestHomeDashboard(IntegrationTestCase):
    def test_estructura_y_pendientes(self):
        """El payload trae las claves esperadas y las 8 tarjetas de pendientes."""
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

    def test_riesgo_critico_se_cuenta_y_el_sin_evaluar_no(self):
        """Solo los riesgos abiertos con nivel Alto/Extremo entran en la tarjeta.

        Un riesgo sin `Evaluacion Riesgo` es dato faltante, no dato grave: no se
        cuenta como crítico (regla: no se infiere nada que no esté enlazado).
        """
        base = _valor(resumen_inicio(), "riesgos_criticos")
        _insertar("Riesgo", {"titulo": f"Riesgo sin evaluar {next(_seq)}"})
        self.assertEqual(_valor(resumen_inicio(), "riesgos_criticos"), base)

        critico = _insertar("Riesgo", {"titulo": f"Riesgo critico {next(_seq)}"})
        # `nivel` es calculado y read_only desde el recorrido 13, y la evaluación
        # exige probabilidad e impacto: se inserta válida y el nivel se fija por
        # debajo, que es el dato que el panel lee.
        evaluacion = _insertar("Evaluacion Riesgo", {
            "riesgo": critico.name, "momento": "Residual",
            "probabilidad": 5, "impacto": 5, "fecha": "2026-01-01",
        })
        frappe.db.set_value("Evaluacion Riesgo", evaluacion.name, "nivel", "Extremo",
                            update_modified=False)
        self.assertEqual(_valor(resumen_inicio(), "riesgos_criticos"), base + 1)

    def test_hallazgo_abierto_se_cuenta(self):
        """'Abierto' y 'Escalado a NC' cuentan; 'Cerrado' no."""
        base = _valor(resumen_inicio(), "hallazgos_abiertos")
        # La auditoría se crea en 'Planificada' (su validate() exige equipo y
        # criterios a partir de 'En ejecucion').
        aud = _insertar("Auditoria", {"titulo": f"Auditoria home {next(_seq)}"})
        _insertar("Hallazgo Auditoria", {"auditoria": aud.name, "tipo": "Observacion", "estado": "Abierto"})
        # con el workflow de f16 activo no se puede nacer en un estado no inicial:
        # se crea Abierto y se lleva a Cerrado por BD, que es lo que el contador lee
        _cerrado = _insertar("Hallazgo Auditoria", {"auditoria": aud.name, "tipo": "Fortaleza", "estado": "Abierto"})
        frappe.db.set_value("Hallazgo Auditoria", _cerrado.name, "estado", "Cerrado",
                            update_modified=False)
        self.assertEqual(_valor(resumen_inicio(), "hallazgos_abiertos"), base + 1)

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
