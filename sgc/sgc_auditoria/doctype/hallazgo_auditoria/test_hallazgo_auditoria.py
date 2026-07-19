# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Suite de tests para el M06 — Hallazgo Auditoria (escalamiento a M05).

Verifica:
  - Autogeneración del código HAU-{anio}-NNNN (autoname field:codigo).
  - `escalar_a_no_conformidad`: crea la No Conformidad (origen Auditoria), marca
    el hallazgo (no_conformidad, genera_nc=1, estado "Escalado a NC"), es
    idempotente y rechaza tipos que no constituyen no conformidad (Conformidad).
  - Auto-sync (Fase 2, brecha Evidencia Enlace / Trazabilidad): una fila en el
    picklist `evidencia` (Table MultiSelect de Evidencia Enlace) crea su
    Trazabilidad correspondiente al guardar (destino `criterio_incumplido`
    y/o `proceso`), marcada `origen=Auto-sincronizado`, idempotente, y no crea
    nada sin destino (evita el "vínculo vacío" de `Trazabilidad.validate()`).

La NC tiene Workflow ("No Conformidad SGC") -> se desactiva en setUp para poder
insertarla desde el escalamiento sin WorkflowPermissionError.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

ADMIN = "Administrator"


class IntegrationTestHallazgoAuditoria(IntegrationTestCase):
    """Escalamiento Hallazgo Auditoria -> No Conformidad (puente §2)."""

    def setUp(self):
        factories.desactivar_workflow("Auditoria")
        factories.desactivar_workflow("No Conformidad")
        self.auditoria = self._auditoria()
        # Fase 2 (2026-07-19): `criterio_incumplido` pasó de Small Text a Link
        # (Elemento Marco) -- se necesita un criterio real para los tests.
        marco = factories.crear_marco_prueba()
        self.criterio = marco["criterios"][marco["estandares"][0]][0]
        self.proceso = factories.crear_proceso().name

    # -- helpers ------------------------------------------------------------
    def _auditoria(self):
        doc = frappe.get_doc({
            "doctype": "Auditoria",
            "titulo": "M06 auditoría para hallazgos",
            "tipo": "Interna",
            "estado": "Planificada",
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _hallazgo(self, tipo="No conformidad menor", **overrides):
        vals = {
            "doctype": "Hallazgo Auditoria",
            "auditoria": self.auditoria.name,
            "tipo": tipo,
            "descripcion": "Evidencia objetiva del hallazgo.",
            "criterio_incumplido": self.criterio,
            "estado": "Abierto",
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    # ======================================================================
    # Autogeneración de código
    # ======================================================================
    def test_codigo_autogenerado(self):
        h = self._hallazgo()
        self.assertTrue(h.codigo.startswith("HAU-"))
        self.assertEqual(h.name, h.codigo)

    # ======================================================================
    # Escalamiento a No Conformidad
    # ======================================================================
    def test_escala_a_no_conformidad(self):
        h = self._hallazgo(tipo="No conformidad mayor")
        nc_name = h.escalar_a_no_conformidad()

        self.assertTrue(nc_name)
        nc = frappe.get_doc("No Conformidad", nc_name)
        self.assertEqual(nc.origen_doctype, "Auditoria")
        self.assertEqual(nc.origen_id, self.auditoria.name)
        self.assertEqual(nc.origen_tipo, "Auditoria")
        self.assertEqual(nc.tipo, "No conformidad mayor")
        self.assertEqual(nc.requisito_incumplido, self.criterio)

        # el hallazgo queda marcado como escalado
        h.reload()
        self.assertEqual(h.no_conformidad, nc_name)
        self.assertEqual(h.genera_nc, 1)
        self.assertEqual(h.estado, "Escalado a NC")

    def test_escala_es_idempotente(self):
        h = self._hallazgo()
        primero = h.escalar_a_no_conformidad()
        segundo = h.escalar_a_no_conformidad()
        self.assertEqual(primero, segundo)

    def test_conformidad_no_escala(self):
        h = self._hallazgo(tipo="Conformidad")
        with self.assertRaises(frappe.ValidationError):
            h.escalar_a_no_conformidad()

    def test_no_conformidad_ligada_marca_estado_en_validate(self):
        # Si se liga una NC manualmente, validate() sincroniza genera_nc y estado.
        nc = frappe.get_doc({
            "doctype": "No Conformidad",
            "titulo": "NC manual de prueba",
            "tipo": "No conformidad menor",
            "estado": "Abierta",
        })
        nc.flags.ignore_permissions = True
        nc.insert(ignore_permissions=True)

        h = self._hallazgo(no_conformidad=nc.name)
        self.assertEqual(h.genera_nc, 1)
        self.assertEqual(h.estado, "Escalado a NC")

    # ======================================================================
    # Auto-sync del picklist `evidencia` hacia Trazabilidad (M09)
    # ======================================================================
    def test_agregar_evidencia_crea_trazabilidad_al_guardar(self):
        """Una fila en `evidencia` con `criterio_incumplido` genera su Trazabilidad."""
        ev = factories.crear_evidencia().name
        self._hallazgo(evidencia=[{"evidencia": ev}])  # criterio_incumplido = self.criterio (default)

        self.assertTrue(
            frappe.db.exists("Trazabilidad", {"evidencia": ev, "elemento_marco": self.criterio})
        )

    def test_trazabilidad_auto_sync_marca_origen(self):
        ev = factories.crear_evidencia().name
        self._hallazgo(evidencia=[{"evidencia": ev}])

        origen = frappe.db.get_value(
            "Trazabilidad", {"evidencia": ev, "elemento_marco": self.criterio}, "origen"
        )
        self.assertEqual(origen, "Auto-sincronizado")

    def test_sincroniza_a_proceso_sin_criterio(self):
        """Sin `criterio_incumplido`, con `proceso` -> la Trazabilidad apunta solo al proceso."""
        ev = factories.crear_evidencia().name
        self._hallazgo(criterio_incumplido=None, proceso=self.proceso, evidencia=[{"evidencia": ev}])

        self.assertTrue(
            frappe.db.exists("Trazabilidad", {"evidencia": ev, "proceso": self.proceso})
        )

    def test_sincroniza_a_criterio_y_proceso_a_la_vez(self):
        ev = factories.crear_evidencia().name
        self._hallazgo(proceso=self.proceso, evidencia=[{"evidencia": ev}])

        self.assertTrue(
            frappe.db.exists(
                "Trazabilidad",
                {"evidencia": ev, "elemento_marco": self.criterio, "proceso": self.proceso},
            )
        )

    def test_guardar_dos_veces_no_duplica_trazabilidad(self):
        """Re-guardar el hallazgo sin tocar `evidencia` no duplica la Trazabilidad."""
        ev = factories.crear_evidencia().name
        h = self._hallazgo(evidencia=[{"evidencia": ev}])

        h.descripcion = "re-guardado sin tocar evidencia"
        h.flags.ignore_permissions = True
        h.save(ignore_permissions=True)

        self.assertEqual(
            frappe.db.count("Trazabilidad", {"evidencia": ev, "elemento_marco": self.criterio}),
            1,
        )

    def test_sin_filas_de_evidencia_no_crea_trazabilidad(self):
        """Hallazgo con `criterio_incumplido` pero sin ninguna fila en `evidencia`.

        Usa un criterio PROPIO (prefijo único), no `self.criterio` compartido:
        otros tests de esta clase sí trazan `self.criterio`, y el aislamiento de
        datos idempotentes entre tests no siempre lo revierte -- un conteo
        exacto sobre el criterio compartido daría falso positivo por residuo
        de otro test (mismo patrón ya resuelto en test_evidencia.py).
        """
        arbol = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo="TEST-HAU-SINEVD")
        criterio_propio = arbol["criterios"][arbol["estandares"][0]][0]
        self._hallazgo(criterio_incumplido=criterio_propio)

        self.assertEqual(frappe.db.count("Trazabilidad", {"elemento_marco": criterio_propio}), 0)

    def test_sin_criterio_ni_proceso_no_crea_trazabilidad_aunque_haya_evidencia(self):
        """Sin destino (ni `criterio_incumplido` ni `proceso`) el sync no crea nada:
        crearla chocaría con el "vínculo vacío" que `Trazabilidad.validate()` rechaza."""
        ev = factories.crear_evidencia().name
        self._hallazgo(criterio_incumplido=None, evidencia=[{"evidencia": ev}])

        self.assertEqual(frappe.db.count("Trazabilidad", {"evidencia": ev}), 0)
