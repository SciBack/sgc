# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Suite de tests para `Trazabilidad` (M09) — el vínculo N:M entre una Evidencia
y un elemento del marco y/o un proceso.

Reglas verificadas del controlador (`trazabilidad.py`):
  validate():
    - Vínculo vacío: si no hay `elemento_marco` NI `proceso` -> ValidationError.
    - Vínculo duplicado: misma `evidencia` hacia el mismo destino
      (mismo par elemento_marco/proceso) -> ValidationError.
  Casos que SÍ deben pasar:
    - vínculo solo a elemento_marco, solo a proceso, o a ambos a la vez;
    - misma evidencia a destinos distintos (otro criterio, otro proceso);
    - distinta evidencia al mismo destino;
    - re-guardar (editar) el propio registro no dispara falso duplicado.

Hereda de `frappe.tests.IntegrationTestCase`: cada test corre en su propia
transacción con rollback automático. El dato base lo arman las factories de
`sgc.tests.factories`.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.tests import factories


class IntegrationTestTrazabilidad(IntegrationTestCase):
    """M09 — vínculo Evidencia ↔ elemento del marco / proceso (RNF09)."""

    def setUp(self):
        # Árbol base: marco con estándares y criterios (destinos "elemento_marco").
        self.arbol = factories.crear_marco_prueba(n_estandares=2, n_criterios=3)
        est = self.arbol["estandares"][0]
        self.criterios = self.arbol["criterios"][est]          # 3 criterios valorables
        self.criterio_a = self.criterios[0]
        self.criterio_b = self.criterios[1]
        # Evidencia con soporte por defecto (enlace_url) y un proceso destino.
        self.evidencia = factories.crear_evidencia().name
        self.proceso = factories.crear_proceso().name

    # -- helpers -----------------------------------------------------------
    def _count(self, **filtros):
        return frappe.db.count("Trazabilidad", filtros)

    # -- camino feliz ------------------------------------------------------
    def test_vincula_evidencia_a_elemento_marco(self):
        """Una Trazabilidad con solo elemento_marco se crea correctamente."""
        traz = factories.crear_trazabilidad(self.evidencia, elemento_marco=self.criterio_a)
        self.assertTrue(frappe.db.exists("Trazabilidad", traz.name))
        self.assertEqual(traz.elemento_marco, self.criterio_a)
        self.assertFalse(traz.proceso)

    def test_vincula_evidencia_a_proceso(self):
        """Una Trazabilidad con solo proceso (sin elemento_marco) se crea correctamente."""
        traz = factories.crear_trazabilidad(self.evidencia, proceso=self.proceso)
        self.assertTrue(frappe.db.exists("Trazabilidad", traz.name))
        self.assertEqual(traz.proceso, self.proceso)
        self.assertFalse(traz.elemento_marco)

    def test_vincula_a_elemento_y_proceso_a_la_vez(self):
        """El controlador permite vincular a elemento_marco Y proceso simultáneamente."""
        traz = factories.crear_trazabilidad(
            self.evidencia, elemento_marco=self.criterio_a, proceso=self.proceso
        )
        self.assertTrue(frappe.db.exists("Trazabilidad", traz.name))
        self.assertEqual(traz.elemento_marco, self.criterio_a)
        self.assertEqual(traz.proceso, self.proceso)

    # -- validación: vínculo vacío ----------------------------------------
    def test_vinculo_vacio_es_rechazado(self):
        """Sin elemento_marco NI proceso, la Trazabilidad no traza nada -> falla."""
        with self.assertRaises(frappe.ValidationError):
            factories.crear_trazabilidad(self.evidencia)

    def test_vinculo_vacio_no_persiste_nada(self):
        """Tras el rechazo del vínculo vacío no queda ninguna fila de esa evidencia."""
        with self.assertRaises(frappe.ValidationError):
            factories.crear_trazabilidad(self.evidencia)
        self.assertEqual(self._count(evidencia=self.evidencia), 0)

    # -- validación: duplicados -------------------------------------------
    def test_duplicado_mismo_elemento_marco_es_rechazado(self):
        """Misma evidencia hacia el mismo criterio dos veces -> vínculo duplicado."""
        factories.crear_trazabilidad(self.evidencia, elemento_marco=self.criterio_a)
        with self.assertRaises(frappe.ValidationError):
            factories.crear_trazabilidad(self.evidencia, elemento_marco=self.criterio_a)
        self.assertEqual(
            self._count(evidencia=self.evidencia, elemento_marco=self.criterio_a), 1
        )

    def test_duplicado_mismo_proceso_es_rechazado(self):
        """Misma evidencia hacia el mismo proceso dos veces -> vínculo duplicado."""
        factories.crear_trazabilidad(self.evidencia, proceso=self.proceso)
        with self.assertRaises(frappe.ValidationError):
            factories.crear_trazabilidad(self.evidencia, proceso=self.proceso)
        self.assertEqual(self._count(evidencia=self.evidencia, proceso=self.proceso), 1)

    def test_duplicado_ignora_tipo_vinculo(self):
        """El dedup mira solo el destino: cambiar tipo_vinculo no evita el duplicado."""
        factories.crear_trazabilidad(
            self.evidencia, elemento_marco=self.criterio_a, tipo_vinculo="Cumple"
        )
        with self.assertRaises(frappe.ValidationError):
            factories.crear_trazabilidad(
                self.evidencia, elemento_marco=self.criterio_a, tipo_vinculo="Soporta"
            )

    # -- casos límite: destinos distintos NO son duplicados ----------------
    def test_misma_evidencia_a_criterios_distintos_es_valido(self):
        """La misma evidencia puede respaldar varios criterios (destinos distintos)."""
        factories.crear_trazabilidad(self.evidencia, elemento_marco=self.criterio_a)
        factories.crear_trazabilidad(self.evidencia, elemento_marco=self.criterio_b)
        self.assertEqual(self._count(evidencia=self.evidencia), 2)

    def test_distintas_evidencias_al_mismo_criterio_es_valido(self):
        """Un criterio puede sustentarse en varias evidencias (misma destino, otra evidencia)."""
        otra = factories.crear_evidencia().name
        factories.crear_trazabilidad(self.evidencia, elemento_marco=self.criterio_a)
        factories.crear_trazabilidad(otra, elemento_marco=self.criterio_a)
        self.assertEqual(self._count(elemento_marco=self.criterio_a), 2)

    def test_mismo_elemento_pero_distinto_proceso_no_es_duplicado(self):
        """(ev, criterio, procA) y (ev, criterio, procB) son destinos distintos: ambos válidos."""
        otro_proceso = factories.crear_proceso().name
        factories.crear_trazabilidad(
            self.evidencia, elemento_marco=self.criterio_a, proceso=self.proceso
        )
        factories.crear_trazabilidad(
            self.evidencia, elemento_marco=self.criterio_a, proceso=otro_proceso
        )
        self.assertEqual(
            self._count(evidencia=self.evidencia, elemento_marco=self.criterio_a), 2
        )

    def test_solo_elemento_vs_elemento_mas_proceso_no_colisionan(self):
        """(ev, criterio, sin proceso) y (ev, criterio, con proceso) son destinos distintos."""
        factories.crear_trazabilidad(self.evidencia, elemento_marco=self.criterio_a)
        factories.crear_trazabilidad(
            self.evidencia, elemento_marco=self.criterio_a, proceso=self.proceso
        )
        self.assertEqual(
            self._count(evidencia=self.evidencia, elemento_marco=self.criterio_a), 2
        )

    # -- edición del propio registro --------------------------------------
    def test_reguardar_mismo_registro_no_dispara_falso_duplicado(self):
        """Editar y salvar la misma Trazabilidad (name != self excluye a sí misma)."""
        traz = factories.crear_trazabilidad(
            self.evidencia, elemento_marco=self.criterio_a, tipo_vinculo="Cumple"
        )
        traz.tipo_vinculo = "Soporta"
        traz.flags.ignore_permissions = True
        traz.save(ignore_permissions=True)  # no debe lanzar ValidationError
        self.assertEqual(
            frappe.db.get_value("Trazabilidad", traz.name, "tipo_vinculo"), "Soporta"
        )
