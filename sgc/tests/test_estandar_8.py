# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Los cuatro DocTypes que soportan el Estándar 8 del modelo Coneau de programas.

El estándar se llama «GESTIÓN DE LA INFORMACIÓN» y tiene 6 criterios. Hasta el
2026-09-11 el sistema lo cubría a medias: los indicadores y su medición sí, pero
el ORIGEN del dato vivía como texto libre en `Ficha Indicador.fuente_dato`, no
había forma de declarar qué es un dato íntegro (criterio 8.1) ni de dejar
constancia de que la información llega a quien decide (criterio 8.6).

Estos tests fijan las reglas que hacen que esos cuatro DocTypes sirvan como
evidencia y no solo como tablas: que una fuente automática diga por dónde entra
el dato, que una regla se pueda disparar sobre algo, que descartar una alerta
exija decir por qué, y que un tablero de ámbito acotado no acabe enseñando la
institución entera.
"""

import frappe
from frappe.tests import IntegrationTestCase

from sgc.tests import factories


class IntegrationTestEstandar8(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    # ── Fuente Dato — criterio 8.1 ──────────────────────────────────────────
    def _fuente(self, **overrides):
        vals = {
            "doctype": "Fuente Dato",
            "codigo": f"E8-FTE-{frappe.generate_hash(length=6)}",
            "nombre": "Oracle LAMB",
            "tipo": "Sistema transaccional",
            "responsable": "Administrator",
            "confidencialidad": "Interna",
            "periodicidad": "Semestral",
            "metodo_recojo": "Manual",
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.insert(ignore_permissions=True)
        return doc

    def test_fuente_automatica_exige_protocolo(self):
        """Sin protocolo, quien venga después no sabe por dónde entra el dato."""
        with self.assertRaises(frappe.ValidationError):
            self._fuente(metodo_recojo="Automático")

    def test_fuente_de_baja_no_sigue_siendo_autoritativa(self):
        doc = self._fuente(es_autoritativa=1)
        doc.estado = "Baja"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

    def test_fuente_manual_se_guarda_sin_protocolo(self):
        doc = self._fuente()
        self.assertEqual(doc.name, doc.codigo)

    # ── Regla Validacion — criterio 8.1 ─────────────────────────────────────
    def _regla(self, **overrides):
        vals = {
            "doctype": "Regla Validacion",
            "codigo": f"E8-RV-{frappe.generate_hash(length=6)}",
            "nombre": "Tasa entre 0 y 100",
            "tipo_regla": "Rango",
            "severidad": "Bloqueante",
            "mensaje": "La tasa debe estar entre 0 y 100.",
            "valor_min": 0,
            "valor_max": 100,
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.insert(ignore_permissions=True)
        return doc

    def test_regla_sin_fuente_ni_indicador_no_aplica_a_nada(self):
        with self.assertRaises(frappe.ValidationError):
            self._regla()

    def test_regla_de_rango_con_minimo_mayor_que_maximo(self):
        ind = factories.crear_indicador()
        with self.assertRaises(frappe.ValidationError):
            self._regla(indicador=ind.name, valor_min=100, valor_max=0)

    def test_regla_de_rango_valida(self):
        ind = factories.crear_indicador()
        doc = self._regla(indicador=ind.name)
        self.assertTrue(doc.activa)

    # ── Alerta Indicador — criterio 8.1 ─────────────────────────────────────
    def _alerta(self, **overrides):
        ind = overrides.pop("indicador", None) or factories.crear_indicador().name
        vals = {
            "doctype": "Alerta Indicador",
            "indicador": ind,
            "tipo": "Meta no alcanzada",
            "severidad": "Alta",
            "mensaje": "El indicador quedó por debajo de la meta.",
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.insert(ignore_permissions=True)
        return doc

    def test_alerta_se_codifica_y_se_fecha_sola(self):
        doc = self._alerta()
        self.assertTrue(doc.codigo.startswith("ALE-"))
        self.assertEqual(doc.name, doc.codigo)
        self.assertIsNotNone(doc.fecha_deteccion)

    def test_descartar_una_alerta_exige_justificarlo(self):
        doc = self._alerta()
        doc.estado = "Descartada"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

    def test_al_resolver_se_sella_la_fecha_de_cierre(self):
        doc = self._alerta()
        self.assertIsNone(doc.fecha_cierre)
        doc.estado = "Resuelta"
        doc.save(ignore_permissions=True)
        self.assertIsNotNone(doc.fecha_cierre)

    def test_reabrir_una_alerta_borra_su_cierre(self):
        doc = self._alerta()
        doc.estado = "Resuelta"
        doc.save(ignore_permissions=True)
        doc.estado = "En atención"
        doc.save(ignore_permissions=True)
        self.assertIsNone(doc.fecha_cierre)

    # ── Tablero Indicadores — criterio 8.6 ──────────────────────────────────
    def _tablero(self, indicadores=None, **overrides):
        if indicadores is None:
            indicadores = [{"indicador": factories.crear_indicador().name}]
        vals = {
            "doctype": "Tablero Indicadores",
            "codigo": f"E8-TAB-{frappe.generate_hash(length=6)}",
            "nombre": "Tablero de dirección",
            "rol_destinatario": "System Manager",
            "ambito": "Institucional",
            "indicadores": indicadores,
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.insert(ignore_permissions=True)
        return doc

    def test_tablero_sin_indicadores_no_muestra_nada(self):
        with self.assertRaises(frappe.ValidationError):
            self._tablero(indicadores=[])

    def test_tablero_acotado_exige_su_objeto(self):
        """Un tablero «de programa» sin programa enseñaría toda la institución."""
        with self.assertRaises(frappe.ValidationError):
            self._tablero(ambito="Programa-sede")

    def test_tablero_institucional_limpia_el_ambito_acotado(self):
        ps = factories.crear_programa_sede()
        doc = self._tablero(ambito="Institucional", programa_sede=ps.name)
        self.assertIsNone(doc.programa_sede)

    def test_tablero_no_admite_el_mismo_indicador_dos_veces(self):
        ind = factories.crear_indicador().name
        with self.assertRaises(frappe.ValidationError):
            self._tablero(indicadores=[{"indicador": ind}, {"indicador": ind}])

    def test_las_filas_se_ordenan_solas(self):
        a = factories.crear_indicador().name
        b = factories.crear_indicador().name
        doc = self._tablero(indicadores=[{"indicador": a}, {"indicador": b}])
        self.assertEqual([f.orden for f in doc.indicadores], [1, 2])
