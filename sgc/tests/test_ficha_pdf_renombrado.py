# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests del renombrado de los Print Format heredados (#65).

Los formatos de la ficha se llamaban `Ficha de Caracterizacion UPeU` y
`… UPeU (publico)`: el nombre del cliente dentro del identificador, en el repo
canónico. Un Print Format se identifica POR SU NOMBRE, así que cambiar la
constante no basta — sin renombrar lo que ya existe, `run()` crearía dos formatos
nuevos y dejaría los viejos huérfanos, con el Desk imprimiendo el que estuviera
fijado por defecto.

Lo que se protege aquí es la migración: que el documento se conserve (no se
recree), que el `default_print_format` del DocType siga apuntando al formato
correcto, y que la función no rompa el arranque en los dos casos raros — nombre
viejo inexistente (instalación nueva) y ambos nombres a la vez.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f19_ficha_pdf

VIEJO = "Ficha de Caracterizacion UPeU"
NUEVO = f19_ficha_pdf.PRINT_FORMAT_NAME
DOCTYPE = f19_ficha_pdf.DOCTYPE


class IntegrationTestFichaPdfRenombrado(IntegrationTestCase):
    def tearDown(self):
        # Dejar el sitio con los nombres nuevos, como lo deja el arranque.
        if frappe.db.exists("Print Format", VIEJO):
            frappe.delete_doc("Print Format", VIEJO, force=True, ignore_permissions=True)
        f19_ficha_pdf.run()
        frappe.db.commit()

    # --- helpers -----------------------------------------------------------

    def _crear_con_nombre_viejo(self):
        """Reproduce una instancia anterior a #65: el formato con el nombre del cliente."""
        if frappe.db.exists("Print Format", NUEVO):
            frappe.rename_doc(
                "Print Format", NUEVO, VIEJO,
                force=True, ignore_permissions=True, show_alert=False,
            )
        frappe.db.set_value("DocType", DOCTYPE, "default_print_format", VIEJO)
        frappe.db.commit()

    # --- el caso real ------------------------------------------------------

    def test_renombra_el_formato_heredado(self):
        self._crear_con_nombre_viejo()

        renombrados = f19_ficha_pdf._renombrar_heredados()

        self.assertTrue(frappe.db.exists("Print Format", NUEVO))
        self.assertFalse(
            frappe.db.exists("Print Format", VIEJO),
            "el nombre con el cliente dentro no debe sobrevivir",
        )
        self.assertIn((VIEJO, NUEVO), renombrados, "debe informar de lo que renombró")

    def test_el_renombrado_conserva_el_documento(self):
        """Renombrar, no recrear: si se recreara, se perdería lo que tuviera dentro."""
        self._crear_con_nombre_viejo()
        creacion = frappe.db.get_value("Print Format", VIEJO, "creation")

        f19_ficha_pdf._renombrar_heredados()

        self.assertEqual(
            frappe.db.get_value("Print Format", NUEVO, "creation"),
            creacion,
            "debe ser el mismo documento, no uno nuevo con el nombre bueno",
        )

    def test_el_default_del_doctype_sigue_apuntando_al_formato(self):
        # `rename_doc` actualiza los campos Link; esto lo fija como contrato, porque
        # si dejara de hacerlo el Desk imprimiría el volcado estándar sin avisar.
        self._crear_con_nombre_viejo()

        f19_ficha_pdf._renombrar_heredados()

        self.assertEqual(
            frappe.db.get_value("DocType", DOCTYPE, "default_print_format"),
            NUEVO,
        )

    def test_run_completo_deja_un_solo_formato(self):
        """El caso que se quería evitar: dos formatos, uno huérfano."""
        self._crear_con_nombre_viejo()

        f19_ficha_pdf.run()

        formatos = frappe.get_all(
            "Print Format",
            filters={"doc_type": DOCTYPE, "name": ["like", "Ficha de Caracterizacion%"]},
            pluck="name",
        )
        self.assertIn(NUEVO, formatos)
        self.assertNotIn(VIEJO, formatos, "no debe quedar el heredado como sobrante")

    # --- los dos casos raros -----------------------------------------------

    def test_instalacion_nueva_no_renombra_nada(self):
        # Sin nombre viejo en la base no hay nada que migrar, y no debe fallar.
        renombrados = f19_ficha_pdf._renombrar_heredados()

        self.assertEqual(renombrados, [])

    def test_con_los_dos_nombres_a_la_vez_avisa_y_no_toca(self):
        """Si existen ambos, renombrar destruiría uno. Mejor pararse y decirlo."""
        f19_ficha_pdf.run()  # deja el nuevo
        frappe.get_doc({
            "doctype": "Print Format",
            "name": VIEJO,
            "doc_type": DOCTYPE,
            "print_format_type": "Jinja",
            "standard": "No",
            "custom_format": 1,
            "html": "<div>heredado</div>",
        }).insert(ignore_permissions=True)
        frappe.db.commit()

        renombrados = f19_ficha_pdf._renombrar_heredados()

        self.assertEqual(renombrados, [], "no debe renombrar sobre uno que ya existe")
        self.assertTrue(frappe.db.exists("Print Format", VIEJO), "y no debe borrarlo")
        self.assertTrue(frappe.db.exists("Print Format", NUEVO))
