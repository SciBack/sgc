# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Tests de la Revisión por la Dirección (§9.3): código, validaciones por estado
(entradas §9.3.2 al realizarla; salidas §9.3.3 + acta al cerrarla) y la
consolidación entradas -> salidas.

Revision Direccion tiene Workflow activo ("Revision Direccion SGC"): para poder
mover `estado` libremente en los tests del CONTROLADOR se desactiva en setUp con
`factories.desactivar_workflow(...)` (el rollback lo reactiva entre casos).
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.tests import factories


class IntegrationTestRevisionDireccion(IntegrationTestCase):
    def setUp(self):
        # El DocType tiene Workflow -> desactivarlo para ejercitar el validate por estado.
        factories.desactivar_workflow("Revision Direccion")

    # ------------------------------------------------------------- helpers
    def _crear(self, estado=None, con_entrada=True, con_salidas=False, pdf=None):
        """Crea una Revision Direccion mínima. Devuelve el doc insertado."""
        doc = frappe.new_doc("Revision Direccion")
        doc.titulo = "Revisión por la Dirección de prueba"
        if estado:
            doc.estado = estado
        if pdf:
            doc.pdf = pdf
        if con_entrada:
            doc.append("entradas", {
                "tipo_entrada": "Oportunidades de mejora",
                "resumen": "Se detectó una oportunidad de mejora en admisión.",
            })
        if con_salidas:
            for tipo in ("Oportunidad de mejora", "Cambio en el SGC", "Necesidad de recursos"):
                doc.append("salidas", {
                    "tipo_salida": tipo,
                    "descripcion": f"Decisión sobre {tipo}.",
                    "responsable": "Administrator",
                })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        return doc

    # ------------------------------------------------------------- código / name
    def test_codigo_se_autocompleta_con_el_name(self):
        """Sin `codigo`, se rellena con el name autogenerado RPD-{YYYY}-{##}."""
        doc = self._crear()
        anio = frappe.utils.nowdate()[:4]
        self.assertTrue(doc.name.startswith(f"RPD-{anio}-"))
        self.assertEqual(doc.codigo, doc.name)

    def test_codigo_explicito_se_respeta(self):
        doc = frappe.new_doc("Revision Direccion")
        doc.titulo = "Con código propio"
        doc.codigo = "RPD-MANUAL-001"
        doc.insert(ignore_permissions=True)
        self.assertEqual(doc.codigo, "RPD-MANUAL-001")

    # ------------------------------------------------------------- estado Realizada (§9.3.2)
    def test_realizada_exige_entradas(self):
        with self.assertRaises(frappe.ValidationError):
            self._crear(estado="Realizada", con_entrada=False)

    # Nota: no se testea "entrada sin tipo" porque el Select `tipo_entrada` no
    # tiene opción vacía inicial → Frappe auto-rellena la primera opción, así que
    # ese estado es inalcanzable (la validación del controlador queda como defensa
    # inofensiva). Mismo gotcha que hubo con Cumplimiento CBC.

    def test_realizada_ok_autocompleta_fecha(self):
        doc = self._crear(estado="Realizada", con_entrada=True)
        self.assertEqual(doc.estado, "Realizada")
        self.assertTrue(doc.fecha)

    # ------------------------------------------------------------- estado Cerrada (§9.3.3)
    def test_cerrada_exige_las_tres_salidas_obligatorias(self):
        # Con entrada pero sin las salidas del §9.3.3 -> no cierra.
        with self.assertRaises(frappe.ValidationError):
            self._crear(estado="Cerrada", con_entrada=True, con_salidas=False, pdf="/files/acta.pdf")

    def test_cerrada_exige_acta_pdf(self):
        with self.assertRaises(frappe.ValidationError):
            self._crear(estado="Cerrada", con_entrada=True, con_salidas=True, pdf=None)

    def test_cerrada_exige_responsable_en_cada_salida(self):
        doc = frappe.new_doc("Revision Direccion")
        doc.titulo = "Salida sin responsable"
        doc.estado = "Cerrada"
        doc.pdf = "/files/acta.pdf"
        doc.append("entradas", {"tipo_entrada": "Oportunidades de mejora", "resumen": "x"})
        for tipo in ("Oportunidad de mejora", "Cambio en el SGC", "Necesidad de recursos"):
            doc.append("salidas", {"tipo_salida": tipo, "descripcion": f"Dec {tipo}"})
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_cerrada_camino_feliz(self):
        doc = self._crear(estado="Cerrada", con_entrada=True, con_salidas=True, pdf="/files/acta.pdf")
        self.assertEqual(doc.estado, "Cerrada")
        self.assertEqual(len(doc.salidas), 3)

    # ------------------------------------------------------------- consolidación
    def test_consolidar_salidas_siembra_las_faltantes(self):
        """Desde entradas §9.3.2, genera el esqueleto de las 3 salidas §9.3.3."""
        doc = frappe.new_doc("Revision Direccion")
        doc.titulo = "Para consolidar"
        doc.estado = "Realizada"
        doc.append("entradas", {
            "tipo_entrada": "Oportunidades de mejora",
            "resumen": "Mejorar tiempos de titulación.",
        })
        doc.append("entradas", {
            "tipo_entrada": "Suficiencia de recursos",
            "resumen": "Falta un evaluador adicional.",
        })
        doc.insert(ignore_permissions=True)

        creadas = doc.consolidar_salidas()
        self.assertEqual(creadas, 3)

        tipos = {s.tipo_salida for s in doc.salidas}
        self.assertEqual(
            tipos,
            {"Oportunidad de mejora", "Cambio en el SGC", "Necesidad de recursos"},
        )

        # La descripción de "Oportunidad de mejora" se sembró desde su entrada.
        om = next(s for s in doc.salidas if s.tipo_salida == "Oportunidad de mejora")
        self.assertIn("titulación", om.descripcion)

    def test_consolidar_salidas_es_idempotente(self):
        doc = self._crear(estado="Realizada", con_entrada=True)
        self.assertEqual(doc.consolidar_salidas(), 3)
        # Segunda pasada: no duplica ninguna salida.
        self.assertEqual(doc.consolidar_salidas(), 0)
        self.assertEqual(len(doc.salidas), 3)
