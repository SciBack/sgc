# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Tests de integración del módulo M11 (mejora / CAPA).

Cubre `plan_mejora.py` y `accion_mejora.py` a través del rollup: al insertar,
cambiar o borrar una `Accion Mejora`, el `Plan Mejora` padre recalcula
`avance_pct` (promedio), `fecha_compromiso` (la más tardía) y `semaforo`
(Rojo/Ambar/Verde por vencimiento). También se validan las reglas de avance
implícito por estado y el clamp [0, 100] de la propia `Accion Mejora`.

No hay factory dedicada para Plan/Accion en `sgc.tests.factories`, así que se
construyen con helpers locales. El rollup se persiste vía `frappe.db.set_value`
(update_modified=False), por lo que el plan SIEMPRE se re-lee desde la BD tras
tocar una acción (el doc en memoria queda desactualizado).
"""
import itertools

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from sgc.tests import factories

# Contador para códigos únicos dentro de la transacción de cada test.
_seq = itertools.count(1)


class IntegrationTestPlanMejora(IntegrationTestCase):
    """Integration tests para PlanMejora + AccionMejora (rollup M11)."""

    def setUp(self):
        # Plan Mejora y Accion Mejora tienen Workflow activo en producción (f4);
        # estos tests setean el `estado` directamente para ejercitar el rollup,
        # así que se desactiva el workflow para el caso (se reactiva por rollback).
        factories.desactivar_workflow("Plan Mejora")
        factories.desactivar_workflow("Accion Mejora")

    # ------------------------------------------------------------------
    # Helpers de construcción
    # ------------------------------------------------------------------
    def _plan(self, estado="En ejecucion", **kw):
        doc = frappe.get_doc({
            "doctype": "Plan Mejora",
            "codigo": f"TEST-PLAN-{next(_seq)}",
            "titulo": "Plan de mejora de prueba",
            "estado": estado,
            **kw,
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _accion(self, plan, estado="En ejecucion", avance_pct=0,
                fecha_compromiso=None, **kw):
        doc = frappe.get_doc({
            "doctype": "Accion Mejora",
            "codigo": f"TEST-ACC-{next(_seq)}",
            "plan_mejora": plan.name if hasattr(plan, "name") else plan,
            "descripcion": "Acción de prueba",
            "tipo": "Mejora",
            "estado": estado,
            "avance_pct": avance_pct,
            "fecha_compromiso": fecha_compromiso,
            **kw,
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _plan_val(self, plan, field):
        """Re-lee un campo del plan desde la BD (el rollup persiste vía set_value)."""
        name = plan.name if hasattr(plan, "name") else plan
        return frappe.db.get_value("Plan Mejora", name, field)

    # ------------------------------------------------------------------
    # Avance de la propia Accion Mejora (validate)
    # ------------------------------------------------------------------
    def test_estado_terminal_fuerza_avance_100(self):
        """Ejecutada / Verificada eficaz fijan el avance a 100 aunque se pase 0."""
        plan = self._plan()
        acc = self._accion(plan, estado="Ejecutada", avance_pct=0)
        self.assertEqual(acc.avance_pct, 100)

        acc2 = self._accion(plan, estado="Verificada eficaz", avance_pct=5)
        self.assertEqual(acc2.avance_pct, 100)

    def test_estado_planificada_fuerza_avance_0(self):
        """Planificada fija el avance a 0 aunque se pase un valor mayor."""
        plan = self._plan()
        acc = self._accion(plan, estado="Planificada", avance_pct=80)
        self.assertEqual(acc.avance_pct, 0)

    def test_avance_manual_respetado_en_estados_no_terminales(self):
        """En ejecucion y Verificada no eficaz respetan el % manual del responsable."""
        plan = self._plan()
        en_curso = self._accion(plan, estado="En ejecucion", avance_pct=45)
        self.assertEqual(en_curso.avance_pct, 45)

        no_eficaz = self._accion(plan, estado="Verificada no eficaz", avance_pct=70)
        self.assertEqual(no_eficaz.avance_pct, 70)

    def test_avance_pct_se_clampa_a_rango_0_100(self):
        """El avance manual se acota a [0, 100]."""
        plan = self._plan()
        alto = self._accion(plan, estado="En ejecucion", avance_pct=150)
        self.assertEqual(alto.avance_pct, 100)

        bajo = self._accion(plan, estado="Verificada no eficaz", avance_pct=-20)
        self.assertEqual(bajo.avance_pct, 0)

    # ------------------------------------------------------------------
    # Rollup del avance del plan (promedio)
    # ------------------------------------------------------------------
    def test_plan_sin_acciones_avance_cero(self):
        """Plan recién creado sin acciones: avance 0, sin fecha, semáforo Verde."""
        plan = self._plan()
        self.assertEqual(self._plan_val(plan, "avance_pct"), 0)
        self.assertIsNone(self._plan_val(plan, "fecha_compromiso"))
        self.assertEqual(self._plan_val(plan, "semaforo"), "Verde")

    def test_avance_plan_es_promedio_redondeado(self):
        """avance_pct del plan = promedio (redondeado) del avance de sus acciones."""
        plan = self._plan()
        self._accion(plan, estado="En ejecucion", avance_pct=100)
        self._accion(plan, estado="En ejecucion", avance_pct=60)
        self._accion(plan, estado="En ejecucion", avance_pct=30)
        # (100 + 60 + 30) / 3 = 63.33 -> round -> 63
        self.assertEqual(self._plan_val(plan, "avance_pct"), 63)

    def test_avance_plan_mezcla_estados_terminales(self):
        """El promedio usa el avance efectivo (forzado por estado)."""
        plan = self._plan()
        self._accion(plan, estado="Ejecutada", avance_pct=0)      # -> 100
        self._accion(plan, estado="Planificada", avance_pct=99)   # -> 0
        # promedio(100, 0) = 50
        self.assertEqual(self._plan_val(plan, "avance_pct"), 50)

    def test_cambio_de_avance_de_accion_recalcula_plan(self):
        """Editar el avance de una acción repropaga el promedio al plan."""
        plan = self._plan()
        acc = self._accion(plan, estado="En ejecucion", avance_pct=40)
        self.assertEqual(self._plan_val(plan, "avance_pct"), 40)

        acc.avance_pct = 80
        acc.flags.ignore_permissions = True
        acc.save(ignore_permissions=True)
        self.assertEqual(self._plan_val(plan, "avance_pct"), 80)

    def test_borrar_accion_recalcula_plan(self):
        """Al borrar una acción (on_trash), el plan recalcula sobre las restantes."""
        plan = self._plan()
        completa = self._accion(plan, estado="Ejecutada")          # -> 100
        pendiente = self._accion(plan, estado="Planificada")       # -> 0
        self.assertEqual(self._plan_val(plan, "avance_pct"), 50)

        pendiente.flags.ignore_permissions = True
        pendiente.delete(ignore_permissions=True)
        # Solo queda la acción al 100.
        self.assertEqual(self._plan_val(plan, "avance_pct"), 100)

    # ------------------------------------------------------------------
    # Rollup de fecha_compromiso (la más tardía)
    # ------------------------------------------------------------------
    def test_fecha_compromiso_plan_es_la_mas_tardia(self):
        """fecha_compromiso del plan = máx de las fechas de sus acciones."""
        plan = self._plan()
        temprana = add_days(nowdate(), 5)
        tardia = add_days(nowdate(), 30)
        self._accion(plan, estado="En ejecucion", fecha_compromiso=temprana)
        self._accion(plan, estado="En ejecucion", fecha_compromiso=tardia)
        self.assertEqual(
            getdate(self._plan_val(plan, "fecha_compromiso")),
            getdate(tardia),
        )

    # ------------------------------------------------------------------
    # Rollup del semáforo (RF-C06)
    # ------------------------------------------------------------------
    def test_semaforo_rojo_por_accion_abierta_vencida(self):
        """Una acción abierta con fecha ya vencida pone el plan en Rojo."""
        plan = self._plan()
        self._accion(plan, estado="En ejecucion",
                     fecha_compromiso=add_days(nowdate(), -5))
        self.assertEqual(self._plan_val(plan, "semaforo"), "Rojo")

    def test_semaforo_ambar_por_accion_por_vencer(self):
        """Una acción abierta por vencer en <=15 días pone el plan en Ambar."""
        plan = self._plan()
        self._accion(plan, estado="En ejecucion",
                     fecha_compromiso=add_days(nowdate(), 10))
        self.assertEqual(self._plan_val(plan, "semaforo"), "Ambar")

    def test_semaforo_verde_al_dia(self):
        """Acción abierta con vencimiento lejano (>15 días): plan Verde."""
        plan = self._plan()
        self._accion(plan, estado="En ejecucion",
                     fecha_compromiso=add_days(nowdate(), 40))
        self.assertEqual(self._plan_val(plan, "semaforo"), "Verde")

    def test_semaforo_ignora_acciones_cerradas_aunque_esten_vencidas(self):
        """Una acción Ejecutada vencida no cuenta como abierta: no dispara Rojo."""
        plan = self._plan()
        self._accion(plan, estado="Ejecutada",
                     fecha_compromiso=add_days(nowdate(), -30))
        self.assertEqual(self._plan_val(plan, "semaforo"), "Verde")

    def test_semaforo_plan_cerrado_siempre_verde(self):
        """Un plan Cerrado queda Verde aunque tenga acciones abiertas vencidas."""
        plan = self._plan(estado="Cerrado")
        self._accion(plan, estado="En ejecucion",
                     fecha_compromiso=add_days(nowdate(), -10))
        self.assertEqual(self._plan_val(plan, "semaforo"), "Verde")
