# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Tests de la Revisión por la Dirección (§9.3): código, validaciones por estado
(entradas §9.3.2 al realizarla; salidas §9.3.3 + acta al cerrarla), el sello y el
candado del cierre, y la consolidación entradas -> salidas.

Revision Direccion tiene Workflow activo ("Revision Direccion SGC"): para poder
mover `estado` libremente en los tests del CONTROLADOR se desactiva en setUp con
`factories.desactivar_workflow(...)` (el rollback lo reactiva entre casos).
"""
import frappe
from frappe.permissions import add_permission, update_permission_property
from frappe.tests import IntegrationTestCase

from sgc.sgc_auditoria.doctype.revision_direccion.revision_direccion import (
    ENTRADAS_REQUERIDAS,
)
from sgc.tests import factories

# Rol propio del test: existe solo para tener a alguien con lectura y sin
# escritura sobre Revision Direccion, sin depender de la matriz RBAC del sitio.
ROL_LECTOR = "R15 Lector de prueba"


class IntegrationTestRevisionDireccion(IntegrationTestCase):
    def setUp(self):
        # El DocType tiene Workflow -> desactivarlo para ejercitar el validate por estado.
        factories.desactivar_workflow("Revision Direccion")
        self._usuario_previo = frappe.session.user

    def tearDown(self):
        frappe.set_user(self._usuario_previo)

    # ------------------------------------------------------------- helpers
    def _crear(self, estado=None, con_entradas=True, con_salidas=False, pdf=None):
        """Crea una Revision Direccion mínima. Devuelve el doc insertado.

        `con_entradas` siembra las SEIS entradas del §9.3.2, que es lo que el
        controlador exige para dar la revisión por realizada.
        """
        doc = frappe.new_doc("Revision Direccion")
        doc.titulo = "Revisión por la Dirección de prueba"
        if estado:
            doc.estado = estado
        if pdf:
            doc.pdf = pdf
        if con_entradas:
            self._sembrar_entradas(doc)
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

    def _sembrar_entradas(self, doc):
        """Las seis entradas del §9.3.2, cada una con su resumen."""
        for tipo in ENTRADAS_REQUERIDAS:
            doc.append("entradas", {
                "tipo_entrada": tipo,
                "resumen": f"Lo considerado sobre {tipo}.",
            })

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
            self._crear(estado="Realizada", con_entradas=False)

    def test_realizada_exige_las_seis_entradas_del_932(self):
        """Una entrada suelta no es «considerar» el §9.3.2: son seis incisos acumulativos.

        Recorrido del 2026-08-23: la revisión pasaba a «Realizada» declarando
        solo «Oportunidades de mejora».
        """
        doc = frappe.new_doc("Revision Direccion")
        doc.titulo = "Solo una entrada"
        doc.estado = "Realizada"
        doc.append("entradas", {
            "tipo_entrada": "Oportunidades de mejora",
            "resumen": "Una sola entrada.",
        })
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_realizada_rechaza_una_entrada_sin_contenido(self):
        """Añadir la fila no es considerar el inciso: sin resumen ni fuente, no vale.

        El Select `tipo_entrada` no tiene opción en blanco, así que Frappe
        rellena la primera opción y una fila creada vacía «cubría» el inciso a).
        """
        doc = frappe.new_doc("Revision Direccion")
        doc.titulo = "Con una entrada en blanco"
        doc.estado = "Realizada"
        self._sembrar_entradas(doc)
        doc.entradas[0].resumen = ""
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_entrada_sin_resumen_vale_si_apunta_a_la_evidencia(self):
        """`fuente_id` es contenido: enlazar la evidencia real sustituye al resumen."""
        otra = self._crear()
        doc = frappe.new_doc("Revision Direccion")
        doc.titulo = "Entrada por fuente"
        doc.estado = "Realizada"
        self._sembrar_entradas(doc)
        doc.entradas[0].resumen = ""
        doc.entradas[0].fuente_doctype = "Revision Direccion"
        doc.entradas[0].fuente_id = otra.name
        doc.insert(ignore_permissions=True)
        self.assertEqual(doc.estado, "Realizada")

    def test_realizada_ok_autocompleta_fecha(self):
        doc = self._crear(estado="Realizada", con_entradas=True)
        self.assertEqual(doc.estado, "Realizada")
        self.assertTrue(doc.fecha)

    # ------------------------------------------------------------- estado Cerrada (§9.3.3)
    def test_cerrada_exige_las_tres_salidas_obligatorias(self):
        # Con entradas pero sin las salidas del §9.3.3 -> no cierra.
        with self.assertRaises(frappe.ValidationError):
            self._crear(estado="Cerrada", con_entradas=True, con_salidas=False,
                        pdf="/files/acta.pdf")

    def test_cerrada_exige_acta_pdf(self):
        with self.assertRaises(frappe.ValidationError):
            self._crear(estado="Cerrada", con_entradas=True, con_salidas=True, pdf=None)

    def test_cerrada_exige_responsable_en_cada_salida(self):
        doc = frappe.new_doc("Revision Direccion")
        doc.titulo = "Salida sin responsable"
        doc.estado = "Cerrada"
        doc.pdf = "/files/acta.pdf"
        self._sembrar_entradas(doc)
        for tipo in ("Oportunidad de mejora", "Cambio en el SGC", "Necesidad de recursos"):
            doc.append("salidas", {"tipo_salida": tipo, "descripcion": f"Dec {tipo}"})
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_cerrada_camino_feliz(self):
        doc = self._crear(estado="Cerrada", con_entradas=True, con_salidas=True,
                          pdf="/files/acta.pdf")
        self.assertEqual(doc.estado, "Cerrada")
        self.assertEqual(len(doc.salidas), 3)

    # ------------------------------------------------------------- firma del cierre
    def test_el_cierre_sella_quien_cierra_y_cuando(self):
        """Cerrar es el acto de la alta dirección: lo firma quien lo ejecuta."""
        doc = self._crear(estado="Cerrada", con_entradas=True, con_salidas=True,
                          pdf="/files/acta.pdf")
        self.assertEqual(doc.cerrada_por, frappe.session.user)
        self.assertEqual(str(doc.fecha_cierre), frappe.utils.nowdate())

    def test_cerrada_por_no_es_tecleable(self):
        """Aunque se escriba otro usuario, el sello lo pone el sistema."""
        doc = frappe.new_doc("Revision Direccion")
        doc.titulo = "Firma inventada"
        doc.estado = "Cerrada"
        doc.pdf = "/files/acta.pdf"
        doc.cerrada_por = "Guest"
        self._sembrar_entradas(doc)
        for tipo in ("Oportunidad de mejora", "Cambio en el SGC", "Necesidad de recursos"):
            doc.append("salidas", {
                "tipo_salida": tipo, "descripcion": f"Dec {tipo}", "responsable": "Administrator",
            })
        doc.insert(ignore_permissions=True)
        self.assertEqual(doc.cerrada_por, frappe.session.user)

    def test_reabrir_borra_la_firma_del_cierre(self):
        """Una revisión reabierta no puede seguir exhibiendo el cierre anterior."""
        doc = self._crear(estado="Cerrada", con_entradas=True, con_salidas=True,
                          pdf="/files/acta.pdf")
        doc.estado = "Realizada"
        doc.save(ignore_permissions=True)
        self.assertFalse(doc.cerrada_por)
        self.assertFalse(doc.fecha_cierre)

    # ------------------------------------------------------------- candado del cierre
    def test_la_revision_cerrada_no_se_edita(self):
        """Recorrido del 2026-08-23: la DPGC cambiaba el acta y las decisiones
        DESPUÉS de que el Rectorado cerrara, sin salir de «Cerrada»."""
        doc = self._crear(estado="Cerrada", con_entradas=True, con_salidas=True,
                          pdf="/files/acta.pdf")
        doc.pdf = "/files/acta-cambiada.pdf"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

    def test_reabrir_es_la_via_para_corregirla(self):
        """El candado deja pasar la reapertura, que es lo que dibuja el flujo 15."""
        doc = self._crear(estado="Cerrada", con_entradas=True, con_salidas=True,
                          pdf="/files/acta.pdf")
        doc.estado = "Realizada"
        doc.save(ignore_permissions=True)

        doc.pdf = "/files/acta-corregida.pdf"
        doc.save(ignore_permissions=True)
        self.assertEqual(doc.pdf, "/files/acta-corregida.pdf")

    # ------------------------------------------------------------- consolidación
    def test_consolidar_salidas_siembra_las_faltantes(self):
        """Desde entradas §9.3.2, genera el esqueleto de las 3 salidas §9.3.3."""
        doc = frappe.new_doc("Revision Direccion")
        doc.titulo = "Para consolidar"
        doc.estado = "Realizada"
        self._sembrar_entradas(doc)
        for fila in doc.entradas:
            if fila.tipo_entrada == "Oportunidades de mejora":
                fila.resumen = "Mejorar tiempos de titulación."
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
        doc = self._crear(estado="Realizada", con_entradas=True)
        self.assertEqual(doc.consolidar_salidas(), 3)
        # Segunda pasada: no duplica ninguna salida.
        self.assertEqual(doc.consolidar_salidas(), 0)
        self.assertEqual(len(doc.salidas), 3)

    def test_consolidar_salidas_exige_permiso_de_escritura(self):
        """`run_doc_method` solo pide LECTURA para invocar un método whitelisted.

        Recorrido del 2026-08-23: un Auditor Interno (solo lectura) redactó por
        esta vía las tres salidas del §9.3.3 de la revisión por la dirección,
        porque el método guardaba con `ignore_permissions=True`.
        """
        doc = self._crear(estado="Realizada", con_entradas=True)
        lector = self._usuario_solo_lectura()

        frappe.set_user(lector)
        solo_lectura = frappe.get_doc("Revision Direccion", doc.name)
        with self.assertRaises(frappe.PermissionError):
            solo_lectura.consolidar_salidas()

        frappe.set_user(self._usuario_previo)
        self.assertEqual(len(frappe.get_doc("Revision Direccion", doc.name).salidas), 0)

    def _usuario_solo_lectura(self):
        """Usuario con lectura —y solo lectura— sobre Revision Direccion."""
        if not frappe.db.exists("Role", ROL_LECTOR):
            frappe.get_doc({"doctype": "Role", "role_name": ROL_LECTOR}).insert(
                ignore_permissions=True)

        add_permission("Revision Direccion", ROL_LECTOR, 0)
        update_permission_property("Revision Direccion", ROL_LECTOR, 0, "read", 1, validate=False)
        update_permission_property("Revision Direccion", ROL_LECTOR, 0, "write", 0, validate=False)

        email = "r15-lector@sgc.test"
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.get_doc({
            "doctype": "User", "email": email, "first_name": "R15 lector",
            "send_welcome_email": 0, "roles": [{"role": ROL_LECTOR}],
        }).insert(ignore_permissions=True)
        return email
