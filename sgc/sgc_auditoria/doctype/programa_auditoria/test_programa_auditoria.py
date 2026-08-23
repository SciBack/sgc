# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Suite de tests para el M06 — Programa Auditoria (programa anual).

El controlador (`programa_auditoria.py`) aplica validaciones INCREMENTALES por
etapa según el Select `estado` (Borrador -> Aprobado -> En ejecucion -> Cerrado):
a partir de "Aprobado" exige responsable, y al entrar en "Aprobado" sella quién
aprueba y cuándo. Al cerrar comprueba que no queden auditorías sin concluir.
También autogenera el código PGA-{anio}-NNNN.

Programa Auditoria tiene Workflow ("Programa Auditoria SGC") -> se desactiva en
setUp para poder crear el programa directamente en el estado que cada test
necesita, dejando correr solo las validaciones del CONTROLADOR.

Los dos bloques del final salen de recorrer el flujo 06 en producción el
2026-08-23, y los dos tocan el mismo punto del proceso: el control que la DPGC
ejerce sobre el trabajo del auditor.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from sgc.tests import factories

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

ADMIN = "Administrator"


class IntegrationTestProgramaAuditoria(IntegrationTestCase):
    """Validaciones incrementales por etapa del M06 (Programa Auditoria)."""

    def setUp(self):
        factories.desactivar_workflow("Programa Auditoria")

    # -- helper -------------------------------------------------------------
    def _programa(self, **overrides):
        vals = {
            "doctype": "Programa Auditoria",
            "titulo": "Programa anual de auditorías M06",
            "estado": "Borrador",
        }
        vals.update(overrides)
        doc = frappe.get_doc(vals)
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    def _auditoria(self, programa, estado=None):
        doc = frappe.get_doc({
            "doctype": "Auditoria",
            "titulo": "Auditoría al proceso de admisión",
            "programa_auditoria": programa,
        }).insert(ignore_permissions=True)
        if estado:
            frappe.db.set_value("Auditoria", doc.name, "estado", estado,
                                update_modified=False)
        return doc

    # ======================================================================
    # Autogeneración de código
    # ======================================================================
    def test_codigo_autogenerado(self):
        p = self._programa()
        self.assertTrue(p.codigo.startswith("PGA-"))
        self.assertEqual(p.name, p.codigo)

    def test_codigo_respeta_el_indicado(self):
        p = self._programa(codigo="TEST-PGA-99")
        self.assertEqual(p.name, "TEST-PGA-99")

    # ======================================================================
    # nivel >= 1 — Aprobado
    # ======================================================================
    def test_aprobado_sin_responsable_falla(self):
        """El Jefe de Auditoría Interna sí hay que declararlo: no se adivina."""
        with self.assertRaises(frappe.ValidationError):
            self._programa(estado="Aprobado", aprobado_por=ADMIN)

    def test_aprobado_completo_autocompleta_fecha(self):
        p = self._programa(estado="Aprobado", responsable=ADMIN)
        self.assertEqual(p.estado, "Aprobado")
        self.assertEqual(str(p.fecha_aprobacion), nowdate())

    def test_borrador_minimo_ok(self):
        p = self._programa()
        self.assertEqual(p.estado, "Borrador")

    # ======================================================================
    # La firma de aprobación la pone el acto, no el formulario
    # ======================================================================
    # `aprobado_por` era un Link que rellenaba a mano cualquiera con permiso de
    # edición — y el primero con ese permiso es el auditor que redacta el
    # programa. En el recorrido, el auditor escribió ahí a un tercero, la DPGC
    # aprobó de verdad, y el programa quedó registrando como aprobador a alguien
    # que no lo tocó. Que el workflow impida la autoaprobación no sirve de nada
    # si el REGISTRO de esa firma es tecleable.

    def test_aprobar_registra_a_quien_aprueba(self):
        p = self._programa(estado="Aprobado", responsable=ADMIN)

        self.assertEqual(p.aprobado_por, frappe.session.user)

    def test_lo_que_alguien_escribio_a_mano_no_prevalece(self):
        """El caso exacto del recorrido: el auditor teclea a un tercero."""
        p = self._programa(estado="Aprobado", responsable=ADMIN, aprobado_por="Guest")

        self.assertEqual(p.aprobado_por, frappe.session.user)

    def test_una_reaprobacion_registra_a_quien_aprueba_esta_vez(self):
        """Tras devolver a borrador, la firma vieja no puede quedarse pegada."""
        p = self._programa(estado="Aprobado", responsable=ADMIN)
        frappe.db.set_value("Programa Auditoria", p.name, "aprobado_por", "Guest",
                            update_modified=False)

        p = frappe.get_doc("Programa Auditoria", p.name)
        p.estado = "Borrador"
        p.save(ignore_permissions=True)
        p.estado = "Aprobado"
        p.save(ignore_permissions=True)

        self.assertEqual(p.aprobado_por, frappe.session.user)

    def test_quedarse_en_aprobado_no_reescribe_la_firma(self):
        """Se sella al ENTRAR: un guardado posterior no cambia al aprobador."""
        p = self._programa(estado="Aprobado", responsable=ADMIN)
        frappe.db.set_value("Programa Auditoria", p.name, "aprobado_por", "Guest",
                            update_modified=False)

        p = frappe.get_doc("Programa Auditoria", p.name)
        p.objetivo = "Objetivo corregido."
        p.save(ignore_permissions=True)

        self.assertEqual(p.aprobado_por, "Guest")

    # ======================================================================
    # nivel >= 3 — Cerrado: ISO 19011 cl. 5.6
    # ======================================================================
    # El programa se cerraba con auditorías todavía en «Planificada», y el
    # diagnóstico anual lo leía como programa cumplido.

    def test_no_se_cierra_con_una_auditoria_sin_concluir(self):
        p = self._programa(estado="En ejecucion", responsable=ADMIN)
        auditoria = self._auditoria(p.name)

        p.estado = "Cerrado"
        with self.assertRaises(frappe.ValidationError) as ctx:
            p.save(ignore_permissions=True)

        self.assertIn(auditoria.name, str(ctx.exception))

    def test_se_cierra_cuando_todas_estan_cerradas(self):
        """El camino normal tiene que llegar: si no, el guard es un muro."""
        p = self._programa(estado="En ejecucion", responsable=ADMIN)
        self._auditoria(p.name, estado="Cerrada")

        p.estado = "Cerrado"
        p.save(ignore_permissions=True)

        self.assertEqual(p.estado, "Cerrado")

    def test_un_programa_sin_auditorias_se_cierra(self):
        """No hay nada que esperar, así que el guard no debe estorbar."""
        p = self._programa(estado="En ejecucion", responsable=ADMIN)

        p.estado = "Cerrado"
        p.save(ignore_permissions=True)

        self.assertEqual(p.estado, "Cerrado")
