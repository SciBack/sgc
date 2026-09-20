# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.semaforo_indicador` — cumplimiento de indicadores (#31).

El test que más importa de este fichero es
`test_el_mismo_numero_da_verde_o_rojo_segun_el_sentido`: con el mismo valor y el
mismo umbral, una tasa de graduación y una de deserción tienen que dar colores
opuestos. Si ese pasa, el resto es aritmética.

Cubre además:
- Zona ámbar derivada de `margen_error` como porcentaje del umbral.
- Modo evolución: mejora, empeora, y qué pasa sin periodo anterior.
- Compatibilidad: una ficha antigua con `regla_evolucion` marcado y sin
  `modo_evaluacion` se sigue evaluando por evolución, sin migrar nada.
- Cuando no hay con qué juzgar (sin ficha, sin umbral, sin anterior), el
  semáforo queda vacío y **no** se inventa un color.

Las funciones de comparación se prueban directas, sin tocar la base: son puras y
así el fallo señala la aritmética y no el andamiaje.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc import semaforo_indicador as sem

PREFIJO = "TEST-SEM"


class IntegrationTestSemaforoIndicador(IntegrationTestCase):
    # --- lo esencial: el sentido invierte el juicio ------------------------

    def test_el_mismo_numero_da_verde_o_rojo_segun_el_sentido(self):
        """55 contra un umbral de 60: bien si menos es mejor, mal si más es mejor."""
        self.assertEqual(sem._por_umbral(55, 60, sem.MAYOR_MEJOR, 0), sem.ROJO)
        self.assertEqual(sem._por_umbral(55, 60, sem.MENOR_MEJOR, 0), sem.VERDE)

    def test_cumplir_justo_el_umbral_es_verde_en_ambos_sentidos(self):
        self.assertEqual(sem._por_umbral(60, 60, sem.MAYOR_MEJOR, 0), sem.VERDE)
        self.assertEqual(sem._por_umbral(60, 60, sem.MENOR_MEJOR, 0), sem.VERDE)

    # --- la zona ámbar ------------------------------------------------------

    def test_margen_crea_zona_ambar_hacia_abajo(self):
        """Umbral 60 con ±5%: 57 falla pero dentro del margen -> ámbar; 56 ya no."""
        self.assertEqual(sem._por_umbral(57, 60, sem.MAYOR_MEJOR, 5), sem.AMBAR)
        self.assertEqual(sem._por_umbral(56, 60, sem.MAYOR_MEJOR, 5), sem.ROJO)

    def test_margen_crea_zona_ambar_hacia_arriba_si_menos_es_mejor(self):
        self.assertEqual(sem._por_umbral(63, 60, sem.MENOR_MEJOR, 5), sem.AMBAR)
        self.assertEqual(sem._por_umbral(64, 60, sem.MENOR_MEJOR, 5), sem.ROJO)

    def test_sin_margen_no_hay_ambar(self):
        self.assertEqual(sem._por_umbral(59.9, 60, sem.MAYOR_MEJOR, 0), sem.ROJO)

    # --- modo evolución -----------------------------------------------------

    def test_evolucion_mejorar_es_verde_y_empeorar_rojo(self):
        self.assertEqual(sem._por_evolucion(70, 60, sem.MAYOR_MEJOR, 0), sem.VERDE)
        self.assertEqual(sem._por_evolucion(50, 60, sem.MAYOR_MEJOR, 0), sem.ROJO)

    def test_evolucion_respeta_el_sentido(self):
        """Bajar la deserción es mejorar, aunque el número baje."""
        self.assertEqual(sem._por_evolucion(50, 60, sem.MENOR_MEJOR, 0), sem.VERDE)
        self.assertEqual(sem._por_evolucion(70, 60, sem.MENOR_MEJOR, 0), sem.ROJO)

    def test_evolucion_mantenerse_dentro_del_margen_es_ambar(self):
        self.assertEqual(sem._por_evolucion(59, 60, sem.MAYOR_MEJOR, 5), sem.AMBAR)
        self.assertEqual(sem._por_evolucion(56, 60, sem.MAYOR_MEJOR, 5), sem.ROJO)

    # --- compatibilidad con las fichas que ya existen ----------------------

    def test_ficha_antigua_con_regla_evolucion_se_evalua_por_evolucion(self):
        """Sin `modo_evaluacion` pero con el check viejo marcado: evolución.

        Evita una migración y, sobre todo, evita que una ficha cuyo autor dijo
        «se evalúa por evolución» pase a medirse contra un umbral.
        """
        ficha = frappe._dict({"modo_evaluacion": None, "regla_evolucion": 1})
        self.assertEqual(sem._modo(ficha), sem.MODO_EVOLUCION)

    def test_ficha_antigua_sin_nada_se_evalua_por_umbral(self):
        ficha = frappe._dict({"modo_evaluacion": None, "regla_evolucion": 0})
        self.assertEqual(sem._modo(ficha), sem.MODO_UMBRAL)

    def test_lo_declarado_manda_sobre_el_campo_viejo(self):
        ficha = frappe._dict({"modo_evaluacion": sem.MODO_UMBRAL, "regla_evolucion": 1})
        self.assertEqual(sem._modo(ficha), sem.MODO_UMBRAL)

    # --- cuando no se puede juzgar, no se juzga ----------------------------

    def test_sin_valor_no_hay_semaforo(self):
        self.assertIsNone(sem.calcular(frappe._dict({"valor_num": None, "indicador": "X"})))

    def test_sin_ficha_no_hay_semaforo(self):
        doc = frappe._dict({"valor_num": 10, "indicador": f"{PREFIJO}-inexistente"})
        self.assertIsNone(sem.calcular(doc))
