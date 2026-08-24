# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Quién elaboró el documento tiene que constar, y hasta ahora no constaba.

El flujo documental está diseñado con tres firmas —elaboración, revisión y
aprobación— y el control las pedía solo dos: no se aprueba sin `revisado_por` ni
se publica sin `aprobado_por`, pero `elaborado_por` no lo rellenaba nadie y no lo
exigía nada. Un documento podía recorrer el circuito entero y publicarse sin que
figurase quién lo redactó.

Se detectó recorriendo el flujo en producción, y tenía un efecto que no se ve
mirando el documento: la alerta «documento por revisar» de M17 se dirige a la
DPGC **y a `elaborado_por`**, así que con el campo vacío solo avisaba a la DPGC.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.tests import factories


class IntegrationTestDocumentoControlado(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.proceso = factories.crear_proceso().name

    def test_quien_crea_el_documento_queda_como_elaborador(self):
        """No hay que acordarse de rellenarlo: se toma de quien lo crea."""
        doc = factories.crear_documento_controlado(proceso=self.proceso)

        self.assertEqual(doc.elaborado_por, frappe.session.user)

    def test_un_elaborador_declarado_se_respeta(self):
        """Si alguien registra el documento en nombre de otro, manda lo declarado."""
        doc = factories.crear_documento_controlado(
            proceso=self.proceso, elaborado_por="Administrator")

        self.assertEqual(doc.elaborado_por, "Administrator")

    def test_no_se_envia_a_revision_sin_elaborador(self):
        """La tercera firma se exige igual que las otras dos."""
        doc = factories.crear_documento_controlado(proceso=self.proceso)
        doc.archivo = "/files/cualquiera.pdf"
        doc.save(ignore_permissions=True)
        # se vacía por debajo del controlador, como si viniera de una carga masiva
        frappe.db.set_value("Documento Controlado", doc.name, "elaborado_por", None,
                            update_modified=False)

        doc = frappe.get_doc("Documento Controlado", doc.name)
        doc.estado = "En revision"
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc.save(ignore_permissions=True)

        # «elabor» y no «elaboró»: la aserción no debe romperse porque el
        # mensaje gane o pierda una tilde. Lo que se comprueba es QUÉ falta,
        # no cómo está redactado.
        self.assertIn("elabor", str(ctx.exception))

    def test_no_se_publica_sin_elaborador(self):
        """Y tampoco se llega a publicar con la firma en blanco.

        El documento se lleva por la cadena real —no se puede saltar de Borrador
        a Publicado, el control de transiciones lo impide— y recién en Aprobado
        se vacía el campo, como si lo hubiera dejado así una carga masiva.
        """
        doc = factories.crear_documento_controlado(proceso=self.proceso)
        doc.archivo = "/files/cualquiera.pdf"
        doc.revisado_por = "Administrator"
        doc.aprobado_por = "Administrator"
        doc.save(ignore_permissions=True)
        for estado in ("En revision", "Aprobado"):
            doc.estado = estado
            doc.save(ignore_permissions=True)
        frappe.db.set_value("Documento Controlado", doc.name, "elaborado_por", None,
                            update_modified=False)

        doc = frappe.get_doc("Documento Controlado", doc.name)
        doc.estado = "Publicado"
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc.save(ignore_permissions=True)

        # «elabor» y no «elaboró»: la aserción no debe romperse porque el
        # mensaje gane o pierda una tilde. Lo que se comprueba es QUÉ falta,
        # no cómo está redactado.
        self.assertIn("elabor", str(ctx.exception))
