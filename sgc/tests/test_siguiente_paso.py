# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""De quién es el turno: la pregunta que la pantalla no sabía contestar.

`frappe.model.workflow.get_transitions` devuelve solo las acciones de QUIEN
pregunta. Cuando el documento espera a otro rol devuelve una lista vacía, y la
interfaz decía «no hay acciones disponibles para tu rol en este estado»: cierto,
y completamente inútil. En un flujo con segregación de funciones —donde por
diseño el siguiente paso es de otra persona— eso ocurre en la mitad de los
pasos.

Se vio usando el sistema el 2026-08-24, no validándolo: quien acababa de enviar
un documento a revisión se quedaba sin saber si tenía que esperar, a quién, ni
hasta cuándo.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.siguiente_paso import de


class IntegrationTestSiguientePaso(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.proceso = frappe.get_doc({
            "doctype": "Proceso", "codigo": f"SP-{frappe.generate_hash(length=6)}",
        }).insert(ignore_permissions=True)

    def _documento(self, estado="Borrador"):
        doc = frappe.get_doc({
            "doctype": "Documento Controlado",
            "codigo": f"SP-DOC-{frappe.generate_hash(length=6)}",
            "titulo": "Documento para probar el turno",
            "tipo_documento": "Procedimiento",
            "proceso": self.proceso.name,
        }).insert(ignore_permissions=True)
        if estado != "Borrador":
            frappe.db.set_value("Documento Controlado", doc.name, "estado", estado,
                                update_modified=False)
        return doc.name

    # ------------------------------------------------------------------
    def test_dice_en_que_estado_esta(self):
        nombre = self._documento()

        self.assertEqual(de("Documento Controlado", nombre)["estado"], "Borrador")

    def test_separa_lo_mio_de_lo_de_otros(self):
        """Las dos listas juntas son todo lo que puede pasar ahora."""
        nombre = self._documento("En revision")

        paso = de("Documento Controlado", nombre)

        acciones = {t["accion"] for t in paso["mias"]} | {t["accion"] for t in paso["de_otros"]}
        self.assertEqual(acciones, {"Aprobar", "Observar"})

    def test_lo_de_otros_dice_de_quien_es(self):
        """Sin el rol, «espera a alguien» no sirve para nada."""
        nombre = self._documento("Aprobado")

        de_otros = de("Documento Controlado", nombre)["de_otros"]
        mias = de("Documento Controlado", nombre)["mias"]

        for t in de_otros + mias:
            self.assertTrue(t["rol"], "toda transición tiene que decir su rol")
            self.assertTrue(t["estado_destino"])

    def test_un_estado_terminal_lo_dice(self):
        """«Obsoleto» no tiene salida, y eso también es una respuesta."""
        nombre = self._documento("Obsoleto")

        paso = de("Documento Controlado", nombre)

        self.assertTrue(paso["final"])
        self.assertEqual(paso["mias"], [])
        self.assertEqual(paso["de_otros"], [])

    def test_un_doctype_sin_workflow_no_inventa_nada(self):
        """Un catálogo no tiene ciclo de vida."""
        paso = de("Proceso", self.proceso.name)

        self.assertIsNone(paso["estado"])
        self.assertFalse(paso["final"])

    def test_quien_no_puede_leer_no_pregunta(self):
        """El endpoint es whitelisted: tiene que comprobar permisos él mismo."""
        nombre = self._documento()
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.ValidationError):
                de("Documento Controlado", nombre)
        finally:
            frappe.set_user("Administrator")
