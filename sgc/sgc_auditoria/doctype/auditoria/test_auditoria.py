# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Suite de tests para el M06 — Auditoria (flujo de auditoría interna).

El controlador (`auditoria.py`) aplica validaciones INCREMENTALES por etapa según
el Select `estado`. El orden lo fija el dict `ORDEN`:

    Planificada(0) -> En ejecucion(1) -> Ejecutada(2) -> Informe emitido(3) -> Cerrada(4)

Reglas verificadas:
  En ejecucion (nivel>=1): exige equipo, criterios y un miembro independiente;
                           autocompleta fecha_inicio.
  Ejecutada    (nivel>=2): autocompleta fecha_fin.
  Informe emitido (nivel>=3): exige informe vinculado y que pertenezca a la auditoría.
  Cerrada      (nivel>=4): no se cierra sin informe.

Auditoria tiene Workflow ("Auditoria SGC"): se desactiva en setUp para poder crear
la auditoría directamente en el estado que cada test necesita (sin transicionar),
dejando que corran solo las validaciones del CONTROLADOR.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

ADMIN = "Administrator"


class IntegrationTestAuditoria(IntegrationTestCase):
    """Validaciones incrementales por etapa del M06 (Auditoria)."""

    def setUp(self):
        factories.desactivar_workflow("Auditoria")

    # -- helpers de construcción -------------------------------------------
    def _equipo(self, independiente=True):
        return [{
            "usuario": ADMIN,
            "rol": "Auditor lider",
            "independiente_del_area": 1 if independiente else 0,
        }]

    def _criterios(self):
        return [{"tipo_criterio": "Clausula norma", "referencia": "ISO 9001 7.5"}]

    def _auditoria(self, **overrides):
        vals = {
            "doctype": "Auditoria",
            "titulo": "M06 auditoría de prueba",
            "tipo": "Interna",
            "estado": "Planificada",
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _informe(self, auditoria):
        doc = frappe.get_doc({
            "doctype": "Informe Auditoria",
            "auditoria": auditoria,
            "conclusiones": "Sin no conformidades mayores.",
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    # ======================================================================
    # Planificada — mínima
    # ======================================================================
    def test_planificada_minima_ok(self):
        aud = self._auditoria()
        self.assertEqual(aud.estado, "Planificada")
        # El código lo autogenera Frappe (format:AUD-{YYYY}-{###}).
        self.assertTrue(aud.name.startswith("AUD-"))

    # ======================================================================
    # nivel >= 1 — En ejecucion
    # ======================================================================
    def test_en_ejecucion_sin_equipo_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._auditoria(estado="En ejecucion", criterios=self._criterios())

    def test_en_ejecucion_sin_criterios_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._auditoria(estado="En ejecucion", equipo=self._equipo())

    def test_en_ejecucion_sin_independencia_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._auditoria(
                estado="En ejecucion",
                equipo=self._equipo(independiente=False),
                criterios=self._criterios(),
            )

    def test_en_ejecucion_completa_ok_autocompleta_fecha_inicio(self):
        aud = self._auditoria(
            estado="En ejecucion",
            equipo=self._equipo(),
            criterios=self._criterios(),
        )
        self.assertEqual(aud.estado, "En ejecucion")
        self.assertEqual(str(aud.fecha_inicio), nowdate())

    # ======================================================================
    # nivel >= 2 — Ejecutada
    # ======================================================================
    def test_ejecutada_autocompleta_fecha_fin(self):
        aud = self._auditoria(
            estado="Ejecutada",
            equipo=self._equipo(),
            criterios=self._criterios(),
        )
        self.assertEqual(str(aud.fecha_fin), nowdate())

    # ======================================================================
    # nivel >= 3 — Informe emitido
    # ======================================================================
    def test_informe_emitido_sin_informe_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._auditoria(
                estado="Informe emitido",
                equipo=self._equipo(),
                criterios=self._criterios(),
            )

    def test_informe_emitido_con_informe_de_otra_auditoria_falla(self):
        otra = self._auditoria(titulo="M06 otra auditoría")
        informe_otra = self._informe(otra.name)
        aud = self._auditoria(
            estado="En ejecucion",
            equipo=self._equipo(),
            criterios=self._criterios(),
        )
        aud.informe = informe_otra.name
        aud.estado = "Informe emitido"
        with self.assertRaises(frappe.ValidationError):
            aud.save(ignore_permissions=True)

    def test_informe_emitido_ok(self):
        aud = self._auditoria(
            estado="Ejecutada",
            equipo=self._equipo(),
            criterios=self._criterios(),
        )
        # Crear el informe enlaza de vuelta la auditoría (on_update -> db_set).
        self._informe(aud.name)
        aud.reload()
        aud.estado = "Informe emitido"
        aud.save(ignore_permissions=True)
        self.assertEqual(aud.estado, "Informe emitido")
        self.assertTrue(aud.informe)

    # ======================================================================
    # nivel >= 4 — Cerrada exige informe
    # ======================================================================
    def test_cerrada_sin_informe_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._auditoria(
                estado="Cerrada",
                equipo=self._equipo(),
                criterios=self._criterios(),
            )

    def test_flujo_completo_hasta_cerrada_ok(self):
        aud = self._auditoria(
            estado="Ejecutada",
            equipo=self._equipo(),
            criterios=self._criterios(),
        )
        self._informe(aud.name)
        aud.reload()
        aud.estado = "Informe emitido"
        aud.save(ignore_permissions=True)
        aud.estado = "Cerrada"
        aud.save(ignore_permissions=True)
        self.assertEqual(aud.estado, "Cerrada")
