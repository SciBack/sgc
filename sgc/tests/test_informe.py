# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Suite de tests para `sgc/informe.py` — el consolidador del Informe SINEACE.

`consolidar(autoevaluacion)` NO calcula juicios: es un ensamblador tipado que
junta lo que ya existe (Valoracion Estandar / Valoracion Criterio / Trazabilidad)
en el contrato que itera el Print Format. Estos tests fijan ese contrato.

Contrato verificado (informe.consolidar):
  estructura:
    dict con {cabecera, vigencia, estandares, resumen_valoracion, todas_evidencias}
  cabecera:
    refleja codigo/titulo/marco/estado/alcance de la Autoevaluacion + nombre y
    ente del Marco Normativo; institucion y fecha siempre presentes.
  nivel por estándar (_nivel_de_estandar):
    confirmado + nivel oficial   -> gana el oficial (confirmado=True)
    no confirmado                -> cae al nivel_propuesto del motor (confirmado=False)
    sin Valoracion Estandar      -> "Sin valorar" + semáforo gris
  semáforo:
    NL rojo / L ámbar / LP verde / sin dato gris.
  criterios:
    un dict por criterio del estándar; cumple = juicio o "Sin valorar".
  evidencias (vía Trazabilidad, sobre estándar y/o sus criterios):
    aparecen deduplicadas por código; se unen en `todas_evidencias`.
  vigencia:
    oficial (humano) gana sobre la propuesta del motor; sin ninguna -> "Pendiente".
  caso de error:
    autoevaluación inexistente -> frappe.DoesNotExistError.

Snapshot congelado (Fase 3+4 — inmutabilidad vía submittable nativo):
  Draft (docstatus=0)      -> el informe sigue leyendo Elemento Marco EN VIVO,
                              sin cambios (mismo camino de siempre).
  Cerrada (docstatus=1)    -> el informe lee del `marco_snapshot` congelado en
                              el submit automático (workflow "Cerrar"); una
                              edición posterior al Elemento Marco en vivo NO
                              se refleja en el informe ya generado.
  cabecera                 -> `fecha_congelamiento` presente solo si hay snapshot.
"""
import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase

from sgc import informe
from sgc import scoring
from sgc.tests import factories


def _cerrar_autoevaluacion(ae_name):
    """Recorre la cadena REAL de transiciones de WF_AUTOEVAL hasta "Cerrada".

    Planificada -[Iniciar evaluacion]-> En curso -[Enviar a revision]->
    En revision -[Consolidar]-> Consolidada -[Cerrar]-> Cerrada.

    "Cerrar" es la transición cuyo estado destino tiene doc_status="1" en
    `sgc.setup.f2_workflow.WF_AUTOEVAL` -> dispara el submit automático
    (docstatus 0->1) de Autoevaluacion (is_submittable=1). Requiere el
    workflow ACTIVO (no llamar `factories.desactivar_workflow` antes de esto).
    """
    for accion in ("Iniciar evaluacion", "Enviar a revision", "Consolidar", "Cerrar"):
        doc = frappe.get_doc("Autoevaluacion", ae_name)
        apply_workflow(doc, accion)
    return frappe.get_doc("Autoevaluacion", ae_name)


class IntegrationTestInforme(IntegrationTestCase):
    """Consolidador del Informe de Autoevaluación SINEACE (sgc/informe.py)."""

    def setUp(self):
        # Árbol base: marco con 3 estándares × 3 criterios + escala NL/L/LP.
        self.arbol = factories.crear_marco_prueba(n_estandares=3, n_criterios=3)
        self.marco = self.arbol["marco"]
        self.estandares = self.arbol["estandares"]        # ["TEST-E1", "TEST-E2", "TEST-E3"]
        self.criterios = self.arbol["criterios"]          # {est: [criterios]}
        self.ae = factories.crear_autoevaluacion(self.marco).name

    # -- helpers de lectura -------------------------------------------------
    def _estandar_out(self, ctx, codigo):
        """El bloque del estándar de código `codigo` dentro del consolidado."""
        for e in ctx["estandares"]:
            if e["codigo"] == codigo:
                return e
        return None

    # ======================================================================
    # Estructura del contrato tipado
    # ======================================================================
    def test_estructura_top_level(self):
        ctx = informe.consolidar(self.ae)
        for clave in ("cabecera", "vigencia", "estandares", "resumen_valoracion", "todas_evidencias"):
            self.assertIn(clave, ctx)
        self.assertIsInstance(ctx["estandares"], list)
        self.assertIsInstance(ctx["todas_evidencias"], list)
        # 3 estándares en el marco -> 3 bloques y 3 filas de resumen.
        self.assertEqual(len(ctx["estandares"]), 3)
        self.assertEqual(len(ctx["resumen_valoracion"]), 3)

    def test_cabecera_refleja_autoevaluacion(self):
        ctx = informe.consolidar(self.ae)
        cab = ctx["cabecera"]
        self.assertEqual(cab["codigo"], self.ae)
        self.assertEqual(cab["marco"], self.marco)
        # La factory crea la autoeval en su estado inicial ("Planificada"); el
        # informe refleja ese estado tal cual (Autoevaluacion tiene Workflow, no
        # se fuerza otro estado en los tests).
        self.assertEqual(cab["estado"], "Planificada")
        # Nombre y ente vienen del Marco Normativo creado por la factory.
        self.assertEqual(cab["marco_nombre"], "Marco de prueba TEST")
        self.assertEqual(cab["ente"], "SINEACE")
        # institucion y fecha siempre presentes (con fallback).
        self.assertTrue(cab["institucion"])
        self.assertTrue(cab["fecha"])

    # ======================================================================
    # Nivel por estándar + semáforo
    # ======================================================================
    def test_estandar_lp_propuesto_no_confirmado(self):
        """Todos los criterios Cumple -> nivel_propuesto LP; consolidar lo muestra sin confirmar."""
        est = self.estandares[0]
        factories.valorar_estandar(self.ae, self.criterios[est], default=factories.CUMPLE)

        bloque = self._estandar_out(informe.consolidar(self.ae), est)
        self.assertEqual(bloque["nivel"], "LP")
        self.assertFalse(bloque["confirmado"])
        self.assertEqual(bloque["semaforo"], informe.SEMAFORO_POR_NIVEL["LP"])

    def test_estandar_sin_valorar_semaforo_gris(self):
        """Un estándar sin Valoracion Estandar -> 'Sin valorar' + semáforo gris."""
        est = self.estandares[2]  # sin tocar
        bloque = self._estandar_out(informe.consolidar(self.ae), est)
        self.assertEqual(bloque["nivel"], "Sin valorar")
        self.assertFalse(bloque["confirmado"])
        self.assertEqual(bloque["semaforo"], informe.SEMAFORO_SIN_DATO)

    def test_confirmado_prevalece_sobre_propuesto(self):
        """El motor propone LP, pero el humano confirma L -> gana el oficial confirmado."""
        est = self.estandares[0]
        factories.valorar_estandar(self.ae, self.criterios[est], default=factories.CUMPLE)
        # propuesta persistida = LP
        self.assertEqual(scoring.proponer_nivel_estandar(self.ae, est), "LP")
        # confirmación humana a un nivel distinto
        factories.confirmar_estandar(self.ae, est, "L")

        bloque = self._estandar_out(informe.consolidar(self.ae), est)
        self.assertEqual(bloque["nivel"], "L")
        self.assertTrue(bloque["confirmado"])
        self.assertEqual(bloque["semaforo"], informe.SEMAFORO_POR_NIVEL["L"])

    def test_nivel_nl_semaforo_rojo(self):
        est = self.estandares[1]
        factories.valorar_estandar(self.ae, self.criterios[est], juicios={0: factories.NO_CUMPLE})
        bloque = self._estandar_out(informe.consolidar(self.ae), est)
        self.assertEqual(bloque["nivel"], "NL")
        self.assertEqual(bloque["semaforo"], informe.SEMAFORO_POR_NIVEL["NL"])

    # ======================================================================
    # Criterios consolidados
    # ======================================================================
    def test_criterios_reflejan_juicio_o_sin_valorar(self):
        est = self.estandares[0]
        crits = self.criterios[est]
        # Valoramos solo el primero; el resto queda sin valorar.
        factories.valorar_criterio(self.ae, crits[0], factories.CUMPLE)

        bloque = self._estandar_out(informe.consolidar(self.ae), est)
        self.assertEqual(len(bloque["criterios"]), len(crits))
        # El criterio valorado muestra su juicio; los demás "Sin valorar".
        por_ref = {c["ref_id"]: c["cumple"] for c in bloque["criterios"]}
        self.assertEqual(por_ref[crits[0]], "Cumple")
        self.assertEqual(por_ref[crits[1]], "Sin valorar")
        self.assertEqual(por_ref[crits[2]], "Sin valorar")

    # ======================================================================
    # Evidencias vía Trazabilidad
    # ======================================================================
    def test_evidencia_via_trazabilidad_en_criterio(self):
        est = self.estandares[0]
        crit = self.criterios[est][0]
        ev = factories.crear_evidencia(titulo="Acta de comité")
        factories.crear_trazabilidad(ev, elemento_marco=crit)

        bloque = self._estandar_out(informe.consolidar(self.ae), est)
        ids = [e["ev_id"] for e in bloque["evidencias"]]
        self.assertIn(ev.name, ids)
        fila = next(e for e in bloque["evidencias"] if e["ev_id"] == ev.name)
        self.assertEqual(fila["titulo"], "Acta de comité")

    def test_evidencia_via_trazabilidad_en_estandar(self):
        est = self.estandares[0]
        ev = factories.crear_evidencia()
        factories.crear_trazabilidad(ev, elemento_marco=est)

        bloque = self._estandar_out(informe.consolidar(self.ae), est)
        self.assertIn(ev.name, [e["ev_id"] for e in bloque["evidencias"]])

    def test_evidencia_deduplicada_entre_estandar_y_criterio(self):
        """Una misma evidencia trazada al estándar Y a un criterio suyo aparece una sola vez."""
        est = self.estandares[0]
        crit = self.criterios[est][0]
        ev = factories.crear_evidencia()
        factories.crear_trazabilidad(ev, elemento_marco=est)
        factories.crear_trazabilidad(ev, elemento_marco=crit)

        bloque = self._estandar_out(informe.consolidar(self.ae), est)
        ocurrencias = [e for e in bloque["evidencias"] if e["ev_id"] == ev.name]
        self.assertEqual(len(ocurrencias), 1)

    def test_todas_evidencias_es_union_deduplicada(self):
        """`todas_evidencias` reúne las evidencias de todos los estándares, sin repetir."""
        e0, e1 = self.estandares[0], self.estandares[1]
        ev_a = factories.crear_evidencia(codigo="TEST-EVD-A")
        ev_b = factories.crear_evidencia(codigo="TEST-EVD-B")
        factories.crear_trazabilidad(ev_a, elemento_marco=e0)
        factories.crear_trazabilidad(ev_b, elemento_marco=e1)
        # ev_a también en un criterio de e1 -> no debe duplicar en la unión.
        factories.crear_trazabilidad(ev_a, elemento_marco=self.criterios[e1][0])

        ctx = informe.consolidar(self.ae)
        ids = [e["ev_id"] for e in ctx["todas_evidencias"]]
        self.assertIn("TEST-EVD-A", ids)
        self.assertIn("TEST-EVD-B", ids)
        self.assertEqual(ids.count("TEST-EVD-A"), 1)
        # Orden estable por código de evidencia.
        self.assertEqual(ids, sorted(ids))

    def test_uri_toma_archivo_real(self):
        """`uri` sale de archivo/almacenamiento_uri (no de enlace_url)."""
        est = self.estandares[0]
        ev = factories.crear_evidencia(codigo="TEST-EVD-URI", almacenamiento_uri="s3://bucket/acta.pdf")
        factories.crear_trazabilidad(ev, elemento_marco=est)

        bloque = self._estandar_out(informe.consolidar(self.ae), est)
        fila = next(e for e in bloque["evidencias"] if e["ev_id"] == ev.name)
        self.assertEqual(fila["uri"], "s3://bucket/acta.pdf")

    def test_estandar_sin_evidencias_lista_vacia(self):
        est = self.estandares[0]
        bloque = self._estandar_out(informe.consolidar(self.ae), est)
        self.assertEqual(bloque["evidencias"], [])

    # ======================================================================
    # Vigencia
    # ======================================================================
    def test_vigencia_pendiente_por_defecto(self):
        vig = informe.consolidar(self.ae)["vigencia"]
        self.assertEqual(vig["oficial"], "")
        self.assertEqual(vig["propuesta"], "")
        self.assertEqual(vig["texto"], "Pendiente")

    def test_vigencia_oficial_prevalece_sobre_propuesta(self):
        """Si el humano fijó resultado_vigencia, ese es el texto (por encima de la propuesta del motor)."""
        # Propuesta del motor: dejamos una propuesta cualquiera.
        frappe.db.set_value("Autoevaluacion", self.ae, "vigencia_propuesta", "Acreditado 3 anios")
        # Resultado oficial confirmado por el humano.
        frappe.db.set_value("Autoevaluacion", self.ae, "resultado_vigencia", "Acreditado 6 años")

        vig = informe.consolidar(self.ae)["vigencia"]
        self.assertEqual(vig["oficial"], "Acreditado 6 años")
        self.assertEqual(vig["propuesta"], "Acreditado 3 anios")
        self.assertEqual(vig["texto"], "Acreditado 6 años")

    # ======================================================================
    # Resumen y orden
    # ======================================================================
    def test_resumen_coincide_con_estandares(self):
        """Cada fila de resumen_valoracion tiene nivel y semáforo alineados a su estándar."""
        est = self.estandares[0]
        factories.valorar_estandar(self.ae, self.criterios[est], default=factories.CUMPLE)

        ctx = informe.consolidar(self.ae)
        por_codigo_est = {e["codigo"]: e for e in ctx["estandares"]}
        for fila in ctx["resumen_valoracion"]:
            bloque = por_codigo_est[fila["codigo"]]
            self.assertEqual(fila["nivel"], bloque["nivel"])
            self.assertEqual(fila["semaforo"], bloque["semaforo"])

    def test_estandares_en_orden_natural(self):
        """E1..E3 en orden natural (no lexicográfico)."""
        codigos = [e["codigo"] for e in informe.consolidar(self.ae)["estandares"]]
        self.assertEqual(codigos, ["TEST-E1", "TEST-E2", "TEST-E3"])

    # ======================================================================
    # Caso de error
    # ======================================================================
    def test_autoevaluacion_inexistente_lanza(self):
        with self.assertRaises(frappe.DoesNotExistError):
            informe.consolidar("TEST-AE-NO-EXISTE-999")

    # ======================================================================
    # Snapshot congelado (Fase 3+4 — inmutabilidad vía submittable nativo)
    # ======================================================================
    # Árbol propio con prefijo dedicado: no comparte datos con el resto de la
    # clase (gotcha ya conocido: crear_marco_prueba sin prefijo único colisiona
    # entre tests) y solo estos tests mueven la Autoevaluacion por el workflow.

    def test_draft_sin_snapshot_lee_marco_en_vivo(self):
        """En Draft (docstatus=0) el informe sigue leyendo Elemento Marco EN VIVO
        y la cabecera NO trae fecha/versión de congelamiento — cero cambios de
        comportamiento respecto de antes del snapshot."""
        self.assertEqual(frappe.db.get_value("Autoevaluacion", self.ae, "docstatus"), 0)

        ctx = informe.consolidar(self.ae)
        self.assertEqual(ctx["cabecera"]["fecha_congelamiento"], "")
        self.assertEqual(ctx["cabecera"]["version_marco_congelado"], "")

        bloque = self._estandar_out(ctx, self.estandares[0])
        self.assertEqual(bloque["denominacion"], "Estandar de prueba 1")

    def test_snapshot_congela_denominacion_tras_cierre(self):
        """Tras Cerrar (submit automático), editar el Elemento Marco EN VIVO
        NO cambia retroactivamente un informe ya generado -- se sigue leyendo
        la denominación ORIGINAL desde `marco_snapshot`, no la editada."""
        arbol = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo="TESTSNAP")
        est = arbol["estandares"][0]
        crit = arbol["criterios"][est][0]
        ae = factories.crear_autoevaluacion(arbol, prefijo="TESTSNAP").name

        # Valora el único criterio para que el estándar quede con un nivel.
        factories.valorar_criterio(ae, crit, factories.CUMPLE)

        ae_doc = _cerrar_autoevaluacion(ae)
        self.assertEqual(ae_doc.docstatus, 1)
        self.assertEqual(ae_doc.estado, "Cerrada")

        # Denominación ORIGINAL, tal como la ve el informe antes de editar.
        bloque_antes = self._estandar_out(informe.consolidar(ae), est)
        self.assertEqual(bloque_antes["denominacion"], "Estandar de prueba 1")

        # Edición en vivo del Elemento Marco DESPUÉS del cierre.
        frappe.db.set_value("Elemento Marco", est, "denominacion", "Denominación EDITADA post-cierre")

        # El informe generado DESPUÉS de la edición sigue mostrando el original.
        bloque_despues = self._estandar_out(informe.consolidar(ae), est)
        self.assertEqual(bloque_despues["denominacion"], "Estandar de prueba 1")
        self.assertNotEqual(bloque_despues["denominacion"], "Denominación EDITADA post-cierre")

    def test_cabecera_cerrada_incluye_fecha_congelamiento(self):
        """La cabecera del informe de una Autoevaluacion cerrada trae fecha y
        versión de congelamiento (ausentes/vacías en una en curso)."""
        arbol = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo="TESTSNAP2")
        est = arbol["estandares"][0]
        crit = arbol["criterios"][est][0]
        ae = factories.crear_autoevaluacion(arbol, prefijo="TESTSNAP2").name
        factories.valorar_criterio(ae, crit, factories.CUMPLE)

        _cerrar_autoevaluacion(ae)

        cab = informe.consolidar(ae)["cabecera"]
        self.assertTrue(cab["fecha_congelamiento"])
        self.assertTrue(cab["version_marco_congelado"])
        self.assertIn(arbol["marco"], cab["version_marco_congelado"])
