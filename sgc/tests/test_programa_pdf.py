# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests del plan anual de auditorías imprimible (#66).

#38 dejó los tres informes formales como Script Reports, que son *resultados*:
se consultan y se exportan. El programa anual es otra cosa — un documento que se
aprueba y se firma ANTES de ejecutar nada, y que un auditor externo pide como
evidencia de que la organización planificó sus auditorías (ISO 19011 cl. 5).

Lo que se protege aquí:

- que el documento **se imprima de verdad**, no solo que el Print Format exista;
- que los datos salgan por `datos_programa()` y no por `as_dict()`, que colaría
  `owner` y `modified_by` en un documento que sale de la institución;
- que un programa **sin auditorías** imprima igual y lo diga, en vez de mostrar
  una tabla vacía sin explicación: el marco se aprueba primero y las auditorías
  se programan después, así que ese estado es legítimo.
"""
import frappe
from frappe.tests import IntegrationTestCase
from frappe.www.printview import get_html_and_style

from sgc.setup import f22_programa_pdf

PF = f22_programa_pdf.PRINT_FORMAT_NAME


class IntegrationTestProgramaPdf(IntegrationTestCase):
    def setUp(self):
        f22_programa_pdf.run()
        self._creados = []

    def tearDown(self):
        for doctype, nombre in reversed(self._creados):
            if frappe.db.exists(doctype, nombre):
                frappe.delete_doc(doctype, nombre, force=True, ignore_permissions=True)
        frappe.db.commit()

    # --- helpers -----------------------------------------------------------

    def _programa(self, **kwargs):
        doc = frappe.get_doc({
            "doctype": "Programa Auditoria",
            "titulo": "Plan anual de auditorías internas",
            "objetivo": "Verificar la conformidad del SGC",
            "alcance": "Todos los procesos misionales",
            "estado": "Borrador",
            **kwargs,
        }).insert(ignore_permissions=True)
        self._creados.append(("Programa Auditoria", doc.name))
        return doc

    def _auditoria(self, programa, **kwargs):
        doc = frappe.get_doc({
            "doctype": "Auditoria",
            "programa_auditoria": programa.name,
            "titulo": "Auditoría interna de procesos",
            "tipo": "Interna",
            "estado": "Planificada",
            **kwargs,
        }).insert(ignore_permissions=True)
        self._creados.append(("Auditoria", doc.name))
        return doc

    def _render(self, programa):
        r = get_html_and_style(
            doc=frappe.get_doc("Programa Auditoria", programa.name).as_json(),
            print_format=PF,
            no_letterhead=1,
        )
        return r.get("html") or ""

    # --- el criterio de aceptación -----------------------------------------

    def test_el_plan_se_imprime(self):
        programa = self._programa()

        html = self._render(programa)

        self.assertIn("Plan Anual de Auditorías Internas", html)
        self.assertIn(programa.codigo or programa.name, html)

    def test_el_plan_lista_sus_auditorias_programadas(self):
        programa = self._programa()
        auditoria = self._auditoria(programa, titulo="Auditoría a Gestión Documental")

        html = self._render(programa)

        self.assertIn(auditoria.name, html, "la auditoría debe aparecer por código")
        self.assertIn("Auditoría a Gestión Documental", html)

    def test_no_lista_auditorias_de_otro_programa(self):
        propio = self._programa()
        ajeno = self._programa(titulo="Otro plan")
        de_otro = self._auditoria(ajeno, titulo="Auditoría del otro plan")

        html = self._render(propio)

        self.assertNotIn(de_otro.name, html)

    # --- el caso legítimo que parece un error ------------------------------

    def test_un_programa_sin_auditorias_imprime_y_lo_explica(self):
        programa = self._programa()

        html = self._render(programa)

        self.assertIn("aún no tiene auditorías registradas", html)
        self.assertNotIn("<tbody>", html, "sin auditorías no debe salir la tabla vacía")

    # --- lo que no puede salir del documento -------------------------------

    def test_no_se_filtran_campos_internos(self):
        """`datos_programa` devuelve campos elegidos, no `as_dict()`.

        Un plan de auditoría sale de la institución. `owner` y `modified_by` son
        correos de personas y no pintan nada en él.
        """
        programa = self._programa()

        datos = frappe.get_doc("Programa Auditoria", programa.name).datos_programa()

        for prohibido in ("owner", "modified_by", "docstatus", "idx"):
            self.assertNotIn(prohibido, datos["programa"])

    def test_el_html_del_modulo_no_nombra_a_ninguna_institucion(self):
        # Mismo contrato que #73: la identidad sale de site_config.
        self.assertNotIn("UNIVERSIDAD PERUANA", f22_programa_pdf.HTML.upper())
        self.assertNotIn("membrete-upeu", f22_programa_pdf.HTML)

    def test_el_formato_queda_por_defecto_en_el_doctype(self):
        # Quien pulse Imprimir debe obtener el plan, no el volcado de campos.
        self.assertEqual(
            frappe.db.get_value("DocType", "Programa Auditoria", "default_print_format"),
            PF,
        )

    def test_es_idempotente(self):
        primera = f22_programa_pdf.run()
        segunda = f22_programa_pdf.run()

        self.assertEqual(primera["print_format"], segunda["print_format"])
        self.assertEqual(segunda["accion"], "actualizado")
