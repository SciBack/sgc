# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Salidas no conformes (#33, ISO 9001 §8.7).

  Controlador (workflow desactivado, para mover el estado a mano)
    - cada etapa exige lo suyo: responsable, decisión, acciones, verificación
    - la concesión exige justificación y no la autoriza quien detectó o registró
    - el resultado no lo verifica quien trató ni quien decidió
    - quién decidió y quién verificó lo sella el sistema, no el formulario
    - devolver a tratamiento exige motivo y deshace el sello de la decisión
  Escalado
    - crea la no conformidad con trazabilidad en ambos sentidos, una sola vez
  Workflow
    - existe, verificar es de la DPGC sin autoaprobación, y el recorrido completo
      por el motor funciona con dos personas
  Informe
    - agrupa por proceso y decisión, con conteo y cantidad afectada

Todo se deshace al final de cada test (rollback de `IntegrationTestCase`).
"""

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase

from sgc.sgc_nucleo.doctype.salida_no_conforme.salida_no_conforme import CONCESION, ORIGEN_NC
from sgc.sgc_nucleo.report.salidas_no_conformes import salidas_no_conformes as informe
from sgc.tests import factories

DOCTYPE = "Salida No Conforme"

DETECTOR = "sgc-prueba-snc-detector@example.com"
DUENO = "sgc-prueba-snc-dueno@example.com"
DPGC = "sgc-prueba-snc-dpgc@example.com"
DPGC_2 = "sgc-prueba-snc-dpgc2@example.com"


def _usuario(correo, *roles):
    """Usuario de prueba. Lleva System Manager para que los permisos del DocType
    no dependan de que el RBAC se haya aplicado en el sitio: lo que se prueba
    aquí es el controlador y el workflow, no la matriz."""
    if frappe.db.exists("User", correo):
        return
    u = frappe.get_doc({"doctype": "User", "email": correo, "first_name": correo.split("@")[0],
                        "send_welcome_email": 0})
    for rol in ("System Manager", *roles):
        u.append("roles", {"role": rol})
    u.insert(ignore_permissions=True)


class _Base(IntegrationTestCase):
    def setUp(self):
        _usuario(DETECTOR, "Auditor Interno")
        _usuario(DUENO, "Dueño de Proceso")
        _usuario(DPGC, "DPGC")
        _usuario(DPGC_2, "DPGC")
        self.proceso = factories.crear_proceso(prefijo="SNC").name

    def tearDown(self):
        frappe.set_user("Administrator")

    def _como(self, usuario):
        frappe.set_user(usuario)
        self.addCleanup(frappe.set_user, "Administrator")

    def _salida(self, **overrides):
        vals = {
            "doctype": DOCTYPE,
            "titulo": "Actas con promedios mal calculados",
            "origen": "Interno",
            "proceso": self.proceso,
            "descripcion": "Tres actas del curso salieron con el promedio ponderado mal.",
            "requisito_incumplido": "Reglamento de evaluación, art. 12.",
            "cantidad_afectada": 3,
            "detectado_por": DETECTOR,
        }
        vals.update(overrides)
        return frappe.get_doc(vals).insert(ignore_permissions=True)


class IntegrationTestSalidaNoConformeControlador(_Base):
    def setUp(self):
        super().setUp()
        factories.desactivar_workflow(DOCTYPE)

    def _en_tratamiento(self, **overrides):
        doc = self._salida(**overrides)
        doc.responsable = DUENO
        doc.estado = "En tratamiento"
        doc.save(ignore_permissions=True)
        return doc

    def _tratada(self, decision="Corregir", como=DUENO, **overrides):
        doc = self._en_tratamiento(**overrides)
        doc.decision = decision
        doc.acciones_tomadas = "Se recalcularon y reemitieron las tres actas."
        if decision == CONCESION:
            doc.justificacion_decision = "El error no altera la condición de aprobado."
        self._como(como)
        doc.estado = "Tratada"
        doc.save(ignore_permissions=True)
        frappe.set_user("Administrator")
        return doc

    # -- alta -----------------------------------------------------------------
    def test_nace_detectada_con_fecha_y_detector(self):
        doc = self._salida(detectado_por=None)
        self.assertEqual(doc.estado, "Detectada")
        self.assertTrue(doc.fecha_deteccion)
        self.assertEqual(doc.detectado_por, "Administrator")
        self.assertTrue(doc.name.startswith("SNC-"))

    def test_la_cantidad_afectada_no_puede_ser_negativa(self):
        with self.assertRaises(frappe.ValidationError):
            self._salida(cantidad_afectada=-1)

    # -- tratamiento ------------------------------------------------------------
    def test_iniciar_el_tratamiento_exige_responsable(self):
        doc = self._salida()
        doc.estado = "En tratamiento"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

    def test_tratar_sin_decision_se_rechaza(self):
        doc = self._en_tratamiento()
        doc.acciones_tomadas = "Algo se hizo."
        doc.estado = "Tratada"
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc.save(ignore_permissions=True)
        self.assertIn("decisión", str(ctx.exception))

    def test_tratar_sin_acciones_se_rechaza(self):
        doc = self._en_tratamiento()
        doc.decision = "Corregir"
        doc.estado = "Tratada"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

    def test_cerrar_sin_decision_se_rechaza(self):
        doc = self._salida()
        doc.responsable = DUENO
        doc.estado = "Cerrada"
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc.save(ignore_permissions=True)
        self.assertIn("decisión", str(ctx.exception))

    def test_tratar_sella_quien_decide_y_cuando(self):
        doc = self._tratada(como=DUENO)
        self.assertEqual(doc.autorizado_por, DUENO)
        self.assertTrue(doc.fecha_tratamiento)

    def test_lo_que_alguien_escriba_en_decidido_por_no_prevalece(self):
        doc = self._en_tratamiento()
        doc.decision = "Corregir"
        doc.acciones_tomadas = "Se reemitieron."
        doc.autorizado_por = DPGC
        self._como(DUENO)
        doc.estado = "Tratada"
        doc.save(ignore_permissions=True)
        self.assertEqual(doc.autorizado_por, DUENO)

    # -- concesión ----------------------------------------------------------------
    def test_concesion_sin_justificacion_se_rechaza(self):
        doc = self._en_tratamiento()
        doc.decision = CONCESION
        doc.acciones_tomadas = "Se entrega como está."
        doc.estado = "Tratada"
        self._como(DUENO)
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc.save(ignore_permissions=True)
        self.assertIn("justificar", str(ctx.exception))

    def test_quien_detecto_no_autoriza_la_concesion(self):
        with self.assertRaises(frappe.ValidationError) as ctx:
            self._tratada(decision=CONCESION, como=DETECTOR)
        self.assertIn("concesión", str(ctx.exception))

    def test_quien_registro_no_autoriza_la_concesion(self):
        """El registrante (owner) y el detector pueden ser personas distintas."""
        with self.assertRaises(frappe.ValidationError):
            self._tratada(decision=CONCESION, como="Administrator")

    def test_otra_persona_si_autoriza_la_concesion(self):
        doc = self._tratada(decision=CONCESION, como=DPGC)
        self.assertEqual(doc.estado, "Tratada")
        self.assertEqual(doc.autorizado_por, DPGC)

    def test_el_detector_si_puede_decidir_corregir(self):
        """La restricción es de la concesión, no de cualquier decisión."""
        doc = self._tratada(decision="Corregir", como=DETECTOR)
        self.assertEqual(doc.autorizado_por, DETECTOR)

    # -- verificación ---------------------------------------------------------------
    def _verificar(self, doc, como=DPGC, marcar=True, evidencia=True):
        if marcar:
            doc.verificacion_conformidad = 1
        if evidencia:
            doc.evidencia_tratamiento = factories.crear_evidencia(prefijo="SNC").name
        self._como(como)
        doc.estado = "Verificada"
        doc.save(ignore_permissions=True)
        frappe.set_user("Administrator")
        return doc

    def test_verificar_sin_marcar_el_resultado_se_rechaza(self):
        doc = self._tratada()
        with self.assertRaises(frappe.ValidationError):
            self._verificar(doc, marcar=False)

    def test_verificar_sin_evidencia_se_rechaza(self):
        doc = self._tratada()
        with self.assertRaises(frappe.ValidationError):
            self._verificar(doc, evidencia=False)

    def test_verificar_completo_sella_quien_y_cuando(self):
        doc = self._verificar(self._tratada())
        self.assertEqual(doc.estado, "Verificada")
        self.assertEqual(doc.verificado_por, DPGC)
        self.assertTrue(doc.fecha_verificacion)

    def test_quien_decidio_no_verifica(self):
        doc = self._tratada(como=DPGC)
        with self.assertRaises(frappe.ValidationError) as ctx:
            self._verificar(doc, como=DPGC)
        self.assertIn("verificar", str(ctx.exception).lower())

    def test_el_responsable_no_verifica(self):
        """Aunque la decisión la firmara otro, quien trató no verifica."""
        doc = self._tratada(como=DUENO)
        frappe.db.set_value(DOCTYPE, doc.name, "responsable", DPGC_2, update_modified=False)
        doc.reload()
        with self.assertRaises(frappe.ValidationError):
            self._verificar(doc, como=DPGC_2)

    def test_cerrar_despues_de_verificar(self):
        doc = self._verificar(self._tratada())
        doc.estado = "Cerrada"
        doc.save(ignore_permissions=True)
        self.assertEqual(doc.estado, "Cerrada")

    # -- devolución -------------------------------------------------------------------
    def test_devolver_sin_motivo_se_rechaza(self):
        doc = self._tratada()
        self._como(DPGC)
        doc.estado = "En tratamiento"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

    def test_devolver_deshace_la_decision_y_firma_la_verificacion(self):
        doc = self._tratada()
        doc.verificacion_conformidad = 1
        doc.observaciones_verificacion = "Faltó reemitir una de las tres actas."
        self._como(DPGC)
        doc.estado = "En tratamiento"
        doc.save(ignore_permissions=True)
        self.assertIsNone(doc.autorizado_por)
        self.assertIsNone(doc.fecha_tratamiento)
        self.assertEqual(doc.verificacion_conformidad, 0)
        self.assertEqual(doc.verificado_por, DPGC)


class IntegrationTestSalidaNoConformeEscalado(_Base):
    def test_escalar_crea_la_nc_enlazada_en_ambos_sentidos(self):
        doc = self._salida()
        nc = doc.escalar_a_no_conformidad()

        origen = frappe.db.get_value(
            "No Conformidad", nc, ["origen_doctype", "origen_id", "origen_tipo", "proceso", "tipo"],
            as_dict=True,
        )
        self.assertEqual(origen.origen_doctype, DOCTYPE)
        self.assertEqual(origen.origen_id, doc.name)
        self.assertEqual(origen.origen_tipo, ORIGEN_NC)
        self.assertEqual(origen.proceso, self.proceso)
        self.assertEqual(origen.tipo, "No conformidad menor")
        doc.reload()
        self.assertEqual(doc.no_conformidad, nc)

    def test_escalar_dos_veces_no_duplica(self):
        doc = self._salida()
        primera = doc.escalar_a_no_conformidad(tipo="No conformidad mayor")
        segunda = doc.escalar_a_no_conformidad()
        self.assertEqual(primera, segunda)
        self.assertEqual(
            frappe.db.count("No Conformidad", {"origen_doctype": DOCTYPE, "origen_id": doc.name}), 1
        )

    def test_escalar_a_un_tipo_que_no_es_nc_se_rechaza(self):
        doc = self._salida()
        with self.assertRaises(frappe.ValidationError):
            doc.escalar_a_no_conformidad(tipo="Observacion")


class IntegrationTestSalidaNoConformeWorkflow(_Base):
    def _workflow(self):
        return frappe.db.get_value("Workflow", {"document_type": DOCTYPE, "is_active": 1}, "name")

    def test_el_workflow_esta_activo_y_verificar_es_de_la_dpgc(self):
        wf = self._workflow()
        self.assertIsNotNone(wf, "Salida No Conforme debe tener workflow (f23)")
        verificar = frappe.get_all(
            "Workflow Transition", filters={"parent": wf, "action": "Verificar"},
            fields=["allowed", "allow_self_approval"],
        )
        self.assertTrue(verificar)
        for t in verificar:
            self.assertEqual(t.allowed, "DPGC")
            self.assertFalse(t.allow_self_approval)

    def test_recorrido_completo_por_el_motor(self):
        """Detectada -> En tratamiento -> Tratada -> Verificada -> Cerrada con dos personas."""
        if not self._workflow():
            self.skipTest("workflow f23 no aplicado en este sitio")

        doc = self._salida()
        frappe.db.set_value(DOCTYPE, doc.name, "responsable", DUENO, update_modified=False)

        self._como(DUENO)
        doc = apply_workflow(frappe.get_doc(DOCTYPE, doc.name), "Iniciar tratamiento")
        self.assertEqual(doc.estado, "En tratamiento")

        frappe.db.set_value(DOCTYPE, doc.name, {
            "decision": "Corregir",
            "acciones_tomadas": "Se reemitieron las actas.",
        }, update_modified=False)
        doc = apply_workflow(frappe.get_doc(DOCTYPE, doc.name), "Registrar tratamiento")
        self.assertEqual(doc.estado, "Tratada")
        self.assertEqual(doc.autorizado_por, DUENO)

        frappe.set_user("Administrator")
        frappe.db.set_value(DOCTYPE, doc.name, {
            "verificacion_conformidad": 1,
            "evidencia_tratamiento": factories.crear_evidencia(prefijo="SNC").name,
        }, update_modified=False)
        self._como(DPGC)
        doc = apply_workflow(frappe.get_doc(DOCTYPE, doc.name), "Verificar")
        self.assertEqual(doc.estado, "Verificada")
        self.assertEqual(doc.verificado_por, DPGC)

        doc = apply_workflow(frappe.get_doc(DOCTYPE, doc.name), "Cerrar")
        self.assertEqual(doc.estado, "Cerrada")

    def test_la_concesion_del_detector_se_rechaza_tambien_por_el_motor(self):
        if not self._workflow():
            self.skipTest("workflow f23 no aplicado en este sitio")
        _usuario("sgc-prueba-snc-dueno-detector@example.com", "Dueño de Proceso")
        detector = "sgc-prueba-snc-dueno-detector@example.com"
        doc = self._salida(detectado_por=detector)
        frappe.db.set_value(DOCTYPE, doc.name, {
            "responsable": detector,
            "estado": "En tratamiento",
            "decision": CONCESION,
            "acciones_tomadas": "Se entrega como está.",
            "justificacion_decision": "No afecta al resultado.",
        }, update_modified=False)
        self._como(detector)
        with self.assertRaises(frappe.ValidationError):
            apply_workflow(frappe.get_doc(DOCTYPE, doc.name), "Registrar tratamiento")


class IntegrationTestInformeSalidasNoConformes(_Base):
    def setUp(self):
        super().setUp()
        factories.desactivar_workflow(DOCTYPE)

    def test_agrupa_por_proceso_y_decision(self):
        otro = factories.crear_proceso(prefijo="SNC").name
        self._salida(cantidad_afectada=3, decision="Corregir")
        self._salida(cantidad_afectada=2, decision="Corregir")
        self._salida(cantidad_afectada=5)
        self._salida(proceso=otro, cantidad_afectada=1, decision="Corregir")

        filas = informe.filas({"proceso": self.proceso})
        por_decision = {f["decision"]: f for f in filas}
        self.assertEqual(set(por_decision), {"Corregir", informe.SIN_DECIDIR})
        self.assertEqual(por_decision["Corregir"]["salidas"], 2)
        self.assertEqual(por_decision["Corregir"]["cantidad_afectada"], 5)
        self.assertEqual(por_decision["Corregir"]["abiertas"], 2)
        self.assertEqual(por_decision[informe.SIN_DECIDIR]["cantidad_afectada"], 5)

    def test_el_detalle_lista_cada_salida_con_los_involucrados(self):
        """Sexto requisito del bloque: informes con los datos de quien intervino."""
        doc = self._salida(fecha_deteccion="2026-02-10")
        doc.responsable = DUENO
        doc.estado = "En tratamiento"
        doc.save(ignore_permissions=True)
        doc.decision = "Corregir"
        doc.acciones_tomadas = "Se reemitieron."
        self._como(DPGC)
        doc.estado = "Tratada"
        doc.save(ignore_permissions=True)
        frappe.set_user("Administrator")
        self._salida(fecha_deteccion="2026-02-11")

        columnas, filas = informe.execute({"proceso": self.proceso, "detalle": 1})
        nombres = [c["fieldname"] for c in columnas]
        for campo in ("detectado_por", "responsable", "autorizado_por", "verificado_por",
                      "proceso", "fecha_deteccion"):
            self.assertIn(campo, nombres)
        self.assertEqual(len(filas), 2)
        fila = next(f for f in filas if f["name"] == doc.name)
        self.assertEqual(fila["detectado_por"], DETECTOR)
        self.assertEqual(fila["responsable"], DUENO)
        self.assertEqual(fila["autorizado_por"], DPGC)
        otra = next(f for f in filas if f["name"] != doc.name)
        self.assertEqual(otra["decision"], informe.SIN_DECIDIR)

    def test_cuenta_las_escaladas_y_filtra_por_fecha(self):
        a = self._salida(fecha_deteccion="2026-01-10")
        self._salida(fecha_deteccion="2026-03-10")
        a.escalar_a_no_conformidad()

        filas = informe.filas({"proceso": self.proceso, "desde": "2026-01-01", "hasta": "2026-01-31"})
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["salidas"], 1)
        self.assertEqual(filas[0]["escaladas"], 1)
