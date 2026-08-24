# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""El menú responde a «qué me toca hacer», no solo a «qué puedo ver».

Filtrar el menú por permiso de LECTURA no filtraba casi nada, y se midió el
2026-08-24 recorriendo el sistema como un Dueño de Proceso real: **trabajaba 4
DocTypes y veía 36** de las 39 entradas. Un Auditor Interno trabajaba 3 y veía
39; el Rectorado trabajaba 1 y veía 39.

Y no es que sobren permisos de lectura: en un sistema de gestión de la calidad
casi todo el mundo puede leer casi todo, y **debe** — un auditor no puede
auditar lo que no ve. Lo que fallaba era la pregunta: el menú contestaba «qué
puedes abrir» cuando quien entra se pregunta «qué tengo que hacer».

`doctypes_de_trabajo` contesta la segunda, y la contesta desde los **workflows
vivos**: si mañana una transición cambia de rol, el menú cambia con ella. Una
lista escrita a mano se desincroniza el primer día y nadie se entera hasta que
alguien no encuentra su trabajo.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.permisos_ui import doctypes_con_flujo, doctypes_de_trabajo, permisos_de_ui


class IntegrationTestPermisosUi(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def _con_rol(self, rol=None):
        """Usuario efímero con un solo rol del SGC (o sin ninguno)."""
        correo = f"perm-ui-{frappe.generate_hash(length=8)}@ejemplo.test"
        doc = frappe.get_doc({
            "doctype": "User", "email": correo, "first_name": "Prueba Permisos",
            "send_welcome_email": 0, "roles": [{"role": rol}] if rol else [],
        }).insert(ignore_permissions=True)
        return doc.name

    # ------------------------------------------------------------------
    def test_devuelve_lo_que_el_rol_ejecuta_en_los_workflows(self):
        """La verdad la tienen las transiciones, no una lista aparte."""
        usuario = self._con_rol("Auditor Interno")

        trabajo = doctypes_de_trabajo(usuario)

        self.assertIn("Auditoria", trabajo)
        self.assertIn("Programa Auditoria", trabajo)
        self.assertIn("Hallazgo Auditoria", trabajo)

    def test_no_devuelve_lo_que_solo_puede_leer(self):
        """El caso exacto del recorrido: leer mucho, ejecutar poco."""
        usuario = self._con_rol("Auditor Interno")

        trabajo = doctypes_de_trabajo(usuario)
        permisos = permisos_de_ui(usuario)

        # Un auditor puede leer el marco normativo —y debe—, pero no ejecuta
        # ninguna acción de flujo sobre él.
        self.assertNotIn("Marco Normativo", trabajo)
        if "Marco Normativo" in permisos:
            self.assertTrue(permisos["Marco Normativo"]["read"])

    def test_trabajar_es_bastante_menos_que_ver(self):
        """Si esto deja de cumplirse, el bloque «Tu trabajo» sobra."""
        usuario = self._con_rol("Auditor Interno")

        trabajo = doctypes_de_trabajo(usuario)
        legibles = [dt for dt, p in permisos_de_ui(usuario).items() if p["read"]]

        self.assertLess(len(trabajo), len(legibles))

    def test_un_rol_de_solo_lectura_trabaja_poco_pero_no_nada(self):
        """El Rectorado ejecuta exactamente un acto: cerrar la revisión."""
        usuario = self._con_rol("Rectorado/VR (lectura)")

        self.assertEqual(doctypes_de_trabajo(usuario), ["Revision Direccion"])

    def test_un_usuario_sin_roles_del_sgc_no_trabaja_nada(self):
        """Y la SPA trata la lista vacía como «no sé», no como «no puedes».

        Sin rol ninguno: Frappe le da igualmente «All» y «Guest», que no
        aparecen en ninguna transición. Se evita nombrar un rol concreto que
        podría no existir en el sitio donde corra la suite.
        """
        usuario = self._con_rol()

        self.assertEqual(doctypes_de_trabajo(usuario), [])

    def test_no_hay_duplicados(self):
        """Un rol con varias transiciones sobre el mismo DocType lo lista una vez."""
        usuario = self._con_rol("DPGC")

        trabajo = doctypes_de_trabajo(usuario)

        self.assertEqual(len(trabajo), len(set(trabajo)))

    def test_sale_ordenado(self):
        """El orden no puede depender de cómo devuelva las filas la base."""
        usuario = self._con_rol("DPGC")

        trabajo = doctypes_de_trabajo(usuario)

        self.assertEqual(trabajo, sorted(trabajo))

    # ------------------------------------------------------------------
    # Qué documentos se mueven por un ciclo de vida
    # ------------------------------------------------------------------
    def test_lista_los_doctypes_con_workflow_activo(self):
        """La SPA pinta sus acciones a partir de esto.

        Sin la lista, el formulario solo sabía guardar y catorce de los quince
        flujos no se podían recorrer desde la aplicación: el documento nacía y
        moría en su estado inicial. Se descubrió usando el sistema, no
        validándolo por API.
        """
        con_flujo = doctypes_con_flujo()

        self.assertIn("Documento Controlado", con_flujo)
        self.assertIn("Riesgo", con_flujo)

    def test_no_lista_los_doctypes_sin_workflow(self):
        """Un catálogo no tiene ciclo de vida: pintarle acciones sería mentir."""
        con_flujo = doctypes_con_flujo()

        self.assertNotIn("Marco Normativo", con_flujo)
        self.assertNotIn("Proceso", con_flujo)

    def test_lo_que_alguien_trabaja_siempre_tiene_flujo(self):
        """Coherencia entre las dos listas del boot: si trabajas algo, se mueve.

        `doctypes_de_trabajo` sale de las transiciones y `doctypes_con_flujo` de
        los workflows, así que la primera no puede contener nada ausente de la
        segunda. Si esto falla, una de las dos consultas dejó de mirar el mismo
        sitio.
        """
        usuario = self._con_rol("DPGC")

        trabajo = set(doctypes_de_trabajo(usuario))
        con_flujo = set(doctypes_con_flujo())

        self.assertTrue(trabajo)
        self.assertTrue(trabajo.issubset(con_flujo), trabajo - con_flujo)
