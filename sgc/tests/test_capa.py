# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Suite de integración para `sgc/capa.py` — la cadena CAPA (F2 §4).

Ejercita el flujo de acción correctiva/preventiva:

    Valoracion Criterio deficiente
        -> generar_hallazgo        (Hallazgo)
        -> escalar_a_no_conformidad (No Conformidad, origen polimórfico)
        -> crear_plan               (Plan Mejora [+ Accion Mejora de ejemplo])

Reglas verificadas (capa.py):
  generar_hallazgo:
    "No cumple"       -> Hallazgo tipo "Debilidad"
    "Cumple parcial"  -> Hallazgo tipo "Oportunidad de mejora"
    "Cumple"/"No aplica" -> None (no dispara)
    idempotente por (origen=Autoevaluacion, autoevaluacion, criterio)
  escalar_a_no_conformidad:
    crea NC con origen_doctype/origen_id/origen_tipo = "Autoevaluacion";
    marca hallazgo.no_conformidad + escalado_a_nc=1; idempotente (doble escalado).
  crear_plan:
    liga Plan Mejora a la NC y setea nc.plan_mejora; cosecha `autoevaluacion`
    cuando la NC vino de una autoevaluación; idempotente; crea (o no) la
    Accion Mejora de ejemplo según `crear_accion_ejemplo`.
  _next_codigo:
    formato `PREFIX-YYYY-####`; robusto a borrados intermedios (nunca colisiona
    con un código ya existente).

Nota de workflow: `No Conformidad` tiene Workflow ACTIVO y `escalar_a_no_conformidad`
inserta la NC con estado "Abierta"; por eso `setUp` desactiva ese workflow para
evitar `WorkflowPermissionError`.
"""
import re

import frappe
from frappe.tests import IntegrationTestCase

from sgc import capa
from sgc.tests import factories


class IntegrationTestCapa(IntegrationTestCase):
    """Cadena CAPA: Hallazgo -> No Conformidad -> Plan Mejora (motor único ISO 9001 §10)."""

    def setUp(self):
        # La NC arranca en estado "Abierta"; con el workflow activo eso rompería.
        factories.desactivar_workflow("No Conformidad")

        # Árbol base: 1 estándar con 3 criterios valorables + escala NL/L/LP.
        self.arbol = factories.crear_marco_prueba(
            n_estandares=1, n_criterios=3, prefijo="TEST-CAPA"
        )
        self.marco = self.arbol["marco"]
        self.estandar = self.arbol["estandares"][0]
        self.criterios = self.arbol["criterios"][self.estandar]   # 3 criterios
        self.ae = factories.crear_autoevaluacion(self.marco, prefijo="TEST-CAPA").name
        self.year = frappe.utils.nowdate()[:4]

    # -- helpers ------------------------------------------------------------
    def _valoracion(self, idx, cumple):
        """Valoracion Criterio del criterio `idx` con el juicio `cumple`."""
        return factories.valorar_criterio(self.ae, self.criterios[idx], cumple)

    def _hallazgo_desde(self, idx, cumple=factories.NO_CUMPLE):
        """Atajo: valora un criterio deficiente y genera su Hallazgo."""
        vc = self._valoracion(idx, cumple)
        return capa.generar_hallazgo(vc.name)

    def _hallazgo_directo(self, codigo):
        """Inserta un Hallazgo con `codigo` explícito (para probar _next_codigo)."""
        doc = frappe.get_doc({
            "doctype": "Hallazgo",
            "codigo": codigo,
            "tipo": "Debilidad",
            "origen": "Autoevaluacion",
            "criterio": self.criterios[0],
            "autoevaluacion": self.ae,
            "descripcion": "hallazgo directo de prueba",
            "estado": "Abierto",
            "fecha": frappe.utils.nowdate(),
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    # ======================================================================
    # Camino feliz: la cadena completa de punta a punta
    # ======================================================================
    def test_cadena_capa_completa(self):
        """Valoracion 'No cumple' -> Hallazgo -> No Conformidad -> Plan Mejora."""
        vc = self._valoracion(0, factories.NO_CUMPLE)

        # 1) Hallazgo
        hallazgo = capa.generar_hallazgo(vc.name)
        self.assertIsNotNone(hallazgo)
        self.assertEqual(hallazgo.tipo, "Debilidad")            # "No cumple" -> Debilidad
        self.assertEqual(hallazgo.origen, "Autoevaluacion")
        self.assertEqual(hallazgo.criterio, self.criterios[0])
        self.assertEqual(hallazgo.autoevaluacion, self.ae)
        self.assertEqual(hallazgo.estado, "Abierto")
        self.assertTrue(hallazgo.codigo.startswith(f"HALL-{self.year}-"))
        self.assertFalse(hallazgo.escalado_a_nc)               # aún no escalado
        self.assertFalse(hallazgo.no_conformidad)

        # 2) No Conformidad (origen polimórfico = Autoevaluacion)
        nc = capa.escalar_a_no_conformidad(hallazgo.name)
        self.assertEqual(nc.tipo, "No conformidad menor")      # Debilidad -> NC menor
        self.assertEqual(nc.origen_doctype, "Autoevaluacion")
        self.assertEqual(nc.origen_id, self.ae)
        self.assertEqual(nc.origen_tipo, "Autoevaluacion")
        self.assertEqual(nc.criterio, self.criterios[0])       # copió el criterio
        self.assertEqual(nc.estado, "Abierta")

        # el hallazgo quedó marcado como escalado y apuntando a la NC
        hallazgo.reload()
        self.assertEqual(hallazgo.no_conformidad, nc.name)
        self.assertTrue(hallazgo.escalado_a_nc)

        # 3) Plan Mejora ligado a la NC
        plan = capa.crear_plan(nc.name)
        self.assertTrue(plan.codigo.startswith(f"PM-{self.year}-"))
        self.assertEqual(plan.origen_doctype, "No Conformidad")
        self.assertEqual(plan.origen_id, nc.name)
        self.assertEqual(plan.estado, "Borrador")
        # cosecha del enlace a la autoevaluación (origen de la NC)
        self.assertEqual(plan.autoevaluacion, self.ae)

        # la NC quedó enlazada al plan
        nc.reload()
        self.assertEqual(nc.plan_mejora, plan.name)

    # ======================================================================
    # generar_hallazgo — tipo según el juicio y guardas
    # ======================================================================
    def test_generar_hallazgo_cumple_parcial_es_oportunidad(self):
        """'Cumple parcial' -> Hallazgo tipo 'Oportunidad de mejora'."""
        hallazgo = self._hallazgo_desde(0, factories.CUMPLE_PARCIAL)
        self.assertIsNotNone(hallazgo)
        self.assertEqual(hallazgo.tipo, "Oportunidad de mejora")

    def test_generar_hallazgo_cumple_no_dispara(self):
        """'Cumple' no es deficiente: generar_hallazgo devuelve None."""
        vc = self._valoracion(0, factories.CUMPLE)
        self.assertIsNone(capa.generar_hallazgo(vc.name))

    def test_generar_hallazgo_no_aplica_no_dispara(self):
        """'No aplica' tampoco dispara hallazgo (fuera del set que lo activa)."""
        vc = self._valoracion(0, factories.NO_APLICA)
        self.assertIsNone(capa.generar_hallazgo(vc.name))

    def test_generar_hallazgo_idempotente(self):
        """Dos llamadas sobre la misma valoración devuelven el MISMO Hallazgo."""
        vc = self._valoracion(0, factories.NO_CUMPLE)
        h1 = capa.generar_hallazgo(vc.name)
        h2 = capa.generar_hallazgo(vc.name)
        self.assertEqual(h1.name, h2.name)
        # no se duplicó en la base para (autoevaluacion, criterio, origen)
        self.assertEqual(
            frappe.db.count("Hallazgo", {
                "autoevaluacion": self.ae,
                "criterio": self.criterios[0],
                "origen": "Autoevaluacion",
            }),
            1,
        )

    def test_generar_hallazgo_valoracion_inexistente_falla(self):
        """Una Valoracion Criterio inexistente hace fallar la lectura del doc."""
        with self.assertRaises(frappe.DoesNotExistError):
            capa.generar_hallazgo("VC-NO-EXISTE-CAPA-XYZ")

    # ======================================================================
    # escalar_a_no_conformidad — idempotencia y tipo de NC
    # ======================================================================
    def test_escalar_idempotente_no_duplica_nc(self):
        """Doble escalado del mismo Hallazgo devuelve la MISMA No Conformidad."""
        hallazgo = self._hallazgo_desde(0)
        nc1 = capa.escalar_a_no_conformidad(hallazgo.name)
        nc2 = capa.escalar_a_no_conformidad(hallazgo.name)
        self.assertEqual(nc1.name, nc2.name)
        # solo existe una NC para esa autoevaluación de origen
        self.assertEqual(
            frappe.db.count("No Conformidad", {
                "origen_doctype": "Autoevaluacion",
                "origen_id": self.ae,
                "criterio": self.criterios[0],
            }),
            1,
        )

    def test_escalar_oportunidad_mejora_conserva_tipo(self):
        """Un Hallazgo 'Oportunidad de mejora' escala a NC tipo 'Oportunidad de mejora'."""
        hallazgo = self._hallazgo_desde(0, factories.CUMPLE_PARCIAL)
        self.assertEqual(hallazgo.tipo, "Oportunidad de mejora")
        nc = capa.escalar_a_no_conformidad(hallazgo.name)
        self.assertEqual(nc.tipo, "Oportunidad de mejora")

    def test_escalar_hallazgo_inexistente_falla(self):
        """Escalar un Hallazgo inexistente hace fallar la lectura del doc."""
        with self.assertRaises(frappe.DoesNotExistError):
            capa.escalar_a_no_conformidad("HALL-NO-EXISTE-CAPA-XYZ")

    # ======================================================================
    # crear_plan — idempotencia y Accion Mejora de ejemplo
    # ======================================================================
    def test_crear_plan_idempotente(self):
        """Dos llamadas sobre la misma NC devuelven el MISMO Plan Mejora."""
        hallazgo = self._hallazgo_desde(0)
        nc = capa.escalar_a_no_conformidad(hallazgo.name)
        p1 = capa.crear_plan(nc.name)
        p2 = capa.crear_plan(nc.name)
        self.assertEqual(p1.name, p2.name)
        self.assertEqual(
            frappe.db.count("Plan Mejora", {
                "origen_doctype": "No Conformidad",
                "origen_id": nc.name,
            }),
            1,
        )

    def test_crear_plan_sin_accion_ejemplo(self):
        """crear_accion_ejemplo=False (defecto): no crea ninguna Accion Mejora."""
        hallazgo = self._hallazgo_desde(0)
        nc = capa.escalar_a_no_conformidad(hallazgo.name)
        plan = capa.crear_plan(nc.name)   # sin flag
        self.assertEqual(
            frappe.db.count("Accion Mejora", {"plan_mejora": plan.name}), 0
        )

    def test_crear_plan_con_accion_ejemplo(self):
        """crear_accion_ejemplo=True: agrega una Accion Mejora inicial (Correctiva)."""
        hallazgo = self._hallazgo_desde(0)
        nc = capa.escalar_a_no_conformidad(hallazgo.name)
        plan = capa.crear_plan(nc.name, crear_accion_ejemplo=True)

        acciones = frappe.get_all(
            "Accion Mejora", filters={"plan_mejora": plan.name}, pluck="name"
        )
        self.assertEqual(len(acciones), 1)
        am = frappe.get_doc("Accion Mejora", acciones[0])
        self.assertEqual(am.tipo, "Correctiva")
        self.assertEqual(am.no_conformidad, nc.name)
        self.assertEqual(am.criterio, self.criterios[0])

    # ======================================================================
    # _next_codigo — formato y robustez ante borrados
    # ======================================================================
    def test_next_codigo_formato(self):
        """El código generado sigue el patrón PREFIX-YYYY-#### y no existe aún."""
        codigo = capa._next_codigo("Hallazgo", "HALL")
        self.assertRegex(codigo, rf"^HALL-{self.year}-\d{{4}}$")
        self.assertFalse(frappe.db.exists("Hallazgo", {"codigo": codigo}))

    def test_next_codigo_robusto_a_borrado_intermedio(self):
        """Tras borrar un código intermedio, el siguiente NUNCA colisiona con uno vivo.

        Se insertan HALL-YYYY-0001/0002/0003, se elimina el 0002 (hueco intermedio)
        y se pide un código nuevo: debe tener formato válido y no chocar con los que
        siguen existiendo (0001, 0003).
        """
        # Banda de códigos por encima del máximo vivo del año: el site puede
        # tener Hallazgos sembrados (demo/CAPA previos) que chocarían con 0001.
        vivos = frappe.get_all(
            "Hallazgo", filters={"codigo": ["like", f"HALL-{self.year}-%"]}, pluck="codigo"
        )
        base = max((int(c.split("-")[-1]) for c in vivos), default=0) + 100
        c1 = f"HALL-{self.year}-{base:04d}"
        c2 = f"HALL-{self.year}-{base + 1:04d}"
        c3 = f"HALL-{self.year}-{base + 2:04d}"
        h1 = self._hallazgo_directo(c1)
        h2 = self._hallazgo_directo(c2)
        h3 = self._hallazgo_directo(c3)

        # borrado intermedio
        frappe.delete_doc("Hallazgo", h2.name, ignore_permissions=True, force=True)
        self.assertFalse(frappe.db.exists("Hallazgo", {"codigo": c2}))

        nuevo = capa._next_codigo("Hallazgo", "HALL")
        # formato correcto
        self.assertRegex(nuevo, rf"^HALL-{self.year}-\d{{4}}$")
        # no colisiona con ningún código vivo
        self.assertNotIn(nuevo, {c1, c3})
        self.assertFalse(frappe.db.exists("Hallazgo", {"codigo": nuevo}))
