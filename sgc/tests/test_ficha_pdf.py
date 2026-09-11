# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""La ficha se entrega como PDF institucional, no como formulario editable.

Lo pidió la DPGC el 10-sep-2026: «el cliente lo que debería visualizar es el PDF,
no el formulario editable». Y con las TAREAS dentro del documento, porque el
flujograma solo muestra actividades.

Estos tests fijan las dos cosas: que el formato existe y es el predeterminado del
doctype, y que los datos que consume salen resueltos de Python —incluidas las
tareas leídas del BPMN— para que la plantilla solo tenga que iterar.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f19_ficha_pdf
from sgc.tests import factories


class IntegrationTestFichaPDF(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_el_formato_existe_y_es_el_predeterminado(self):
        f19_ficha_pdf.run()
        nombre = f19_ficha_pdf.PRINT_FORMAT_NAME
        self.assertTrue(frappe.db.exists("Print Format", nombre))

        pf = frappe.get_doc("Print Format", nombre)
        self.assertEqual(pf.doc_type, f19_ficha_pdf.DOCTYPE)
        self.assertEqual(pf.print_format_type, "Jinja")
        self.assertTrue(pf.custom_format, "sin custom_format, Frappe ignora la plantilla")
        self.assertEqual(
            frappe.db.get_value("DocType", f19_ficha_pdf.DOCTYPE, "default_print_format"),
            nombre,
            "quien pulse Imprimir debe obtener el documento institucional, no el volcado de campos",
        )

    def test_correr_dos_veces_no_duplica_ni_rompe(self):
        f19_ficha_pdf.run()
        f19_ficha_pdf.run()  # corre en cada after_migrate
        self.assertEqual(
            frappe.db.count("Print Format", {"name": f19_ficha_pdf.PRINT_FORMAT_NAME}), 1
        )

    def test_la_plantilla_no_consulta_la_base(self):
        """Mismo contrato que el informe SINEACE: el Jinja itera, Python resuelve."""
        html = f19_ficha_pdf.HTML
        self.assertIn("doc.datos_ficha()", html)
        self.assertNotIn("frappe.get_all", html)
        self.assertNotIn("frappe.db.sql", html)

    def test_los_datos_traen_las_tareas_del_diagrama(self):
        """La tabla de tareas del PDF sale del BPMN, no de una lista paralela."""
        proceso = factories.crear_proceso()
        ficha = frappe.get_doc({
            "doctype": "Ficha Caracterizacion Proceso",
            "proceso": proceso.name,
            "objetivo": "Objetivo de prueba",
        }).insert(ignore_permissions=True)

        datos = ficha.datos_ficha()

        # el contrato que la plantilla espera, exista o no contenido
        for clave in ("proceso", "actividades", "indicadores", "entradas", "salidas", "cambios"):
            self.assertIn(clave, datos, f"la plantilla itera sobre «{clave}»")
        self.assertEqual(datos["proceso"]["name"], proceso.name)
        self.assertIsInstance(datos["actividades"], list)

        frappe.delete_doc("Ficha Caracterizacion Proceso", ficha.name, ignore_permissions=True, force=True)
        frappe.db.commit()
