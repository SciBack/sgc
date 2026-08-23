# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Quién aprueba el programa de auditoría, y cuándo se puede darlo por cerrado.

Dos agujeros que salieron recorriendo el flujo 06 en producción el 2026-08-23,
los dos en el mismo sitio del proceso: el control que la DPGC ejerce sobre el
trabajo del auditor.

El primero: `aprobado_por` era un Link que rellenaba a mano cualquiera con
permiso de edición — y el primero con ese permiso es el propio auditor que
redacta el programa. En el recorrido, el auditor escribió ahí a un tercero, la
DPGC aprobó de verdad, y el programa quedó registrando como aprobador a alguien
que no lo tocó. La segregación de funciones que el workflow sí hace cumplir
(`allow_self_approval=0`) no servía de nada si el *registro* de esa firma era
tecleable.

El segundo: el programa se cerraba con auditorías todavía en «Planificada».
ISO 19011 cl. 5.6 pide revisar el programa contra lo ejecutado antes de darlo
por concluido; sin la regla, una auditoría que nunca se hizo quedaba colgando de
un programa cerrado y el diagnóstico anual lo leía como programa cumplido.
"""
import frappe
from frappe.tests import IntegrationTestCase


def _programa(**overrides):
    doc = frappe.new_doc("Programa Auditoria")
    doc.update({
        "titulo": "Programa anual de auditorías internas",
        "objetivo": "Verificar la conformidad del SGC.",
        "alcance": "Los procesos del mapa institucional.",
        "responsable": "Administrator",
    })
    doc.update(overrides)
    doc.insert(ignore_permissions=True)
    return doc


class IntegrationTestProgramaAuditoria(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    # ------------------------------------------------------------- la firma
    def test_aprobar_registra_a_quien_aprueba(self):
        """La firma la pone el acto, no el formulario."""
        doc = _programa()
        doc.estado = "Aprobado"
        doc.save(ignore_permissions=True)

        self.assertEqual(doc.aprobado_por, frappe.session.user)
        self.assertTrue(doc.fecha_aprobacion)

    def test_lo_que_alguien_escribio_a_mano_no_prevalece(self):
        """Es el caso exacto del recorrido: el auditor teclea a un tercero."""
        doc = _programa(aprobado_por="Guest")
        doc.estado = "Aprobado"
        doc.save(ignore_permissions=True)

        self.assertEqual(doc.aprobado_por, frappe.session.user)

    def test_una_reaprobacion_registra_a_quien_aprueba_esta_vez(self):
        """Tras devolver a borrador, la firma vieja no puede quedarse pegada."""
        doc = _programa()
        doc.estado = "Aprobado"
        doc.save(ignore_permissions=True)
        frappe.db.set_value("Programa Auditoria", doc.name, "aprobado_por", "Guest",
                            update_modified=False)

        doc = frappe.get_doc("Programa Auditoria", doc.name)
        doc.estado = "Borrador"
        doc.save(ignore_permissions=True)
        doc.estado = "Aprobado"
        doc.save(ignore_permissions=True)

        self.assertEqual(doc.aprobado_por, frappe.session.user)

    def test_quedarse_en_aprobado_no_reescribe_la_firma(self):
        """Se sella al ENTRAR: un guardado posterior no cambia al aprobador."""
        doc = _programa()
        doc.estado = "Aprobado"
        doc.save(ignore_permissions=True)
        frappe.db.set_value("Programa Auditoria", doc.name, "aprobado_por", "Guest",
                            update_modified=False)

        doc = frappe.get_doc("Programa Auditoria", doc.name)
        doc.objetivo = "Objetivo corregido."
        doc.save(ignore_permissions=True)

        self.assertEqual(doc.aprobado_por, "Guest")

    def test_sin_responsable_no_se_aprueba(self):
        """El Jefe de Auditoría Interna sí hay que declararlo: no se adivina."""
        doc = _programa()
        frappe.db.set_value("Programa Auditoria", doc.name, "responsable", None,
                            update_modified=False)

        doc = frappe.get_doc("Programa Auditoria", doc.name)
        doc.estado = "Aprobado"
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc.save(ignore_permissions=True)

        self.assertIn("responsable", str(ctx.exception))

    # ------------------------------------------------------------- el cierre
    def test_no_se_cierra_con_una_auditoria_sin_concluir(self):
        """El caso del recorrido: cerrar dejando una auditoría en «Planificada»."""
        doc = _programa()
        auditoria = frappe.get_doc({
            "doctype": "Auditoria",
            "titulo": "Auditoría al proceso de admisión",
            "programa_auditoria": doc.name,
        }).insert(ignore_permissions=True)

        doc.estado = "Cerrado"
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc.save(ignore_permissions=True)

        self.assertIn(auditoria.name, str(ctx.exception))

    def test_se_cierra_cuando_todas_estan_cerradas(self):
        """El camino normal tiene que llegar: si no, el guard es un muro."""
        doc = _programa()
        auditoria = frappe.get_doc({
            "doctype": "Auditoria",
            "titulo": "Auditoría al proceso de admisión",
            "programa_auditoria": doc.name,
        }).insert(ignore_permissions=True)
        frappe.db.set_value("Auditoria", auditoria.name, "estado", "Cerrada",
                            update_modified=False)

        doc.estado = "Cerrado"
        doc.save(ignore_permissions=True)

        self.assertEqual(doc.estado, "Cerrado")

    def test_un_programa_sin_auditorias_se_cierra(self):
        """No hay nada que esperar, así que el guard no debe estorbar."""
        doc = _programa()
        doc.estado = "Cerrado"
        doc.save(ignore_permissions=True)

        self.assertEqual(doc.estado, "Cerrado")
