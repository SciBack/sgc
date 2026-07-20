# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Pruebas del endpoint público de métricas para la portada de login."""

import re
from datetime import timedelta

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, nowdate

from sgc.login_portada import _CACHE_KEY, metricas_portada
from sgc.tests import factories


class IntegrationTestLoginPortada(IntegrationTestCase):
    PREFIJO = "TEST-LOGIN-PORTADA"

    def setUp(self):
        super().setUp()
        frappe.cache.delete_value(_CACHE_KEY)
        self._user_anterior = frappe.session.user
        frappe.set_user("Administrator")

        # Cada caso controla el universo agregado sin depender de datos semilla.
        for doctype in ("Evidencia", "Autoevaluacion", "Programa Sede"):
            frappe.db.delete(doctype)

    def tearDown(self):
        try:
            frappe.cache.delete_value(_CACHE_KEY)
            frappe.set_user(self._user_anterior)
        finally:
            super().tearDown()

    def _insertar(self, doctype, codigo, **values):
        return frappe.get_doc({"doctype": doctype, "codigo": codigo, **values}).insert(
            ignore_permissions=True
        )

    def _crear_programa_sede(self, sufijo, sede, estado="activo"):
        unidad = self._insertar(
            "Unidad Organica",
            f"{self.PREFIJO}-UO-{sede}",
            nombre=f"Sede {sede}",
        ) if not frappe.db.exists("Unidad Organica", f"{self.PREFIJO}-UO-{sede}") else frappe.get_doc(
            "Unidad Organica", f"{self.PREFIJO}-UO-{sede}"
        )
        programa = self._insertar(
            "Programa",
            f"{self.PREFIJO}-PR-{sufijo}",
            nombre=f"Programa {sufijo}",
        )
        return self._insertar(
            "Programa Sede",
            f"{self.PREFIJO}-PS-{sufijo}",
            programa=programa.name,
            sede=unidad.name,
            estado=estado,
        )

    def _crear_autoevaluacion(self, marco, sufijo, estado, docstatus=0):
        doc = factories.crear_autoevaluacion(
            marco,
            codigo=f"{self.PREFIJO}-AE-{sufijo}",
        )
        frappe.db.set_value(
            "Autoevaluacion",
            doc.name,
            {"estado": estado, "docstatus": docstatus},
            update_modified=False,
        )
        return doc.name

    def test_payload_con_conteos_por_estado_vigencia_y_sede(self):
        self._crear_programa_sede("A1", "A")
        self._crear_programa_sede("A2", "A")
        self._crear_programa_sede("B1", "B")
        self._crear_programa_sede("C1", "C", estado="inactivo")

        marco = factories.crear_marco_prueba(
            n_estandares=1,
            n_criterios=1,
            prefijo=self.PREFIJO,
        )
        self._crear_autoevaluacion(marco, "PLAN", "Planificada")
        self._crear_autoevaluacion(marco, "CURSO", "En curso")
        self._crear_autoevaluacion(marco, "REV", "En revision")
        self._crear_autoevaluacion(marco, "CONS", "Consolidada")
        self._crear_autoevaluacion(marco, "SUB", "En curso", docstatus=1)
        self._crear_autoevaluacion(marco, "CANCEL", "Planificada", docstatus=2)

        hoy = getdate(nowdate())
        factories.crear_evidencia(
            codigo=f"{self.PREFIJO}-EV-HOY", vigencia_hasta=hoy
        )
        factories.crear_evidencia(
            codigo=f"{self.PREFIJO}-EV-FUTURA", vigencia_hasta=hoy + timedelta(days=1)
        )
        factories.crear_evidencia(
            codigo=f"{self.PREFIJO}-EV-VENCIDA", vigencia_hasta=hoy - timedelta(days=1)
        )
        factories.crear_evidencia(codigo=f"{self.PREFIJO}-EV-SIN-VIGENCIA")

        payload = metricas_portada()

        self.assertEqual(
            set(payload), {"programas", "autoevaluaciones", "evidencias", "calculado_en"}
        )
        self.assertEqual(set(payload["programas"]), {"activos", "sedes"})
        self.assertEqual(set(payload["autoevaluaciones"]), {"activas", "total", "pct"})
        self.assertEqual(set(payload["evidencias"]), {"vigentes", "con_vigencia", "pct"})
        self.assertEqual(payload["programas"], {"activos": 3, "sedes": 2})
        self.assertEqual(payload["autoevaluaciones"], {"activas": 3, "total": 5, "pct": 60})
        self.assertEqual(payload["evidencias"], {"vigentes": 2, "con_vigencia": 3, "pct": 67})
        self.assertIsInstance(payload["autoevaluaciones"]["pct"], int)
        self.assertIsInstance(payload["evidencias"]["pct"], int)
        self.assertRegex(payload["calculado_en"], re.compile(r"[+-]\d{2}:\d{2}$"))
        self.assertIn(metricas_portada, frappe.whitelisted)
        self.assertIn(metricas_portada, frappe.guest_methods)

    def test_pct_evidencias_es_none_si_no_hay_vigencias(self):
        factories.crear_evidencia(codigo=f"{self.PREFIJO}-EV-SIN-VIGENCIA")

        self.assertEqual(
            metricas_portada()["evidencias"],
            {"vigentes": 0, "con_vigencia": 0, "pct": None},
        )

    def test_segunda_llamada_usa_cache_aunque_cambie_la_base(self):
        programa = self._crear_programa_sede("CACHE", "CACHE")
        primero = metricas_portada()
        redis_key = frappe.cache.make_key(_CACHE_KEY)
        frappe.local.cache.pop(redis_key, None)
        ttl = frappe.cache.ttl(redis_key)
        self.assertGreaterEqual(ttl, 1)
        self.assertLessEqual(ttl, 300)

        frappe.db.set_value(
            "Programa Sede", programa.name, "estado", "inactivo", update_modified=False
        )
        segundo = metricas_portada()

        self.assertEqual(segundo, primero)
        self.assertEqual(segundo["programas"]["activos"], 1)
