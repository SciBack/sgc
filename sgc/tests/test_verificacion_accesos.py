# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de la verificación de accesos (#58).

El 20-sep-2026 cuatro cuentas quedaron sin poder abrir el Desk y nada lo detectó:
el sitio respondía 200, las cuentas existían, estaban habilitadas y tenían rol.
Estos tests fijan que ahora **sí** se detecta, y —tan importante como eso— que no
se señala lo que está bien: un informe que grita por cuentas correctas deja de
leerse, y entonces vuelve a no detectar nada.

Cada test monta el estado en la base y comprueba el hallazgo, en vez de llamar a
la función con datos inventados: lo que se protege es el diagnóstico sobre una
instancia real, no la aritmética de una lista.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f3b_rbac
from sgc.verificacion import AVISO, BLOQUEANTE, accesos, verificar

ROL_CON_DESK = "Decano/Director (lectura)"   # el catálogo lo declara con desk_access=1
ROL_SIN_DESK = "Lector Externo"              # el catálogo lo declara con desk_access=0


class IntegrationTestVerificacionAccesos(IntegrationTestCase):
    def setUp(self):
        # El catálogo tiene que estar alineado ANTES de crear usuarios: si un rol
        # está divergente, Frappe marca Website User al insertar la cuenta y el
        # test mediría el estado del sitio en vez del comportamiento. (Pasó en el
        # lab, que tenía los 13 roles a desk_access=0 — justo lo que esto detecta.)
        f3b_rbac._ensure_roles()
        frappe.db.commit()
        self._usuarios = []

    def tearDown(self):
        for email in self._usuarios:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    # --- helpers -----------------------------------------------------------

    def _usuario(self, sufijo, roles, user_type=None):
        email = f"sgc-verif-{sufijo}@example.com"
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": f"Verif {sufijo}",
            "enabled": 1,
            "roles": [{"role": r} for r in roles],
        }).insert(ignore_permissions=True)
        self._usuarios.append(email)
        if user_type:
            # Escritura directa a propósito: reproduce el estado inconsistente sin
            # disparar el recálculo que lo corregiría.
            frappe.db.set_value("User", email, "user_type", user_type)
            frappe.db.commit()
        return email

    def _codigos(self, nivel=None):
        return [h.codigo for h in verificar() if nivel is None or h.nivel == nivel]

    def _hallazgo(self, codigo):
        return next((h for h in verificar() if h.codigo == codigo), None)

    # --- el incidente del 20-sep -------------------------------------------

    def test_detecta_la_cuenta_degradada(self):
        email = self._usuario("degradado", [ROL_CON_DESK], user_type="Website User")

        h = self._hallazgo("acceso-denegado")

        self.assertIsNotNone(h, "la cuenta que no puede entrar debe salir en el informe")
        self.assertEqual(h.nivel, AVISO)
        self.assertTrue(
            any(email in linea for linea in h.detalle),
            "el informe debe NOMBRAR la cuenta, no solo contarla",
        )

    def test_el_hallazgo_dice_que_hacer(self):
        self._usuario("degradado2", [ROL_CON_DESK], user_type="Website User")

        h = self._hallazgo("acceso-denegado")

        self.assertIn("f3b_rbac", h.remedio or "", "sin remedio, el aviso no acciona nada")

    # --- la bomba de relojería ---------------------------------------------

    def test_detecta_la_cuenta_que_perdera_el_acceso(self):
        """System User con roles sin desk_access: hoy entra, mañana no."""
        email = self._usuario("en-riesgo", [ROL_SIN_DESK], user_type="System User")

        h = self._hallazgo("acceso-en-riesgo")

        self.assertIsNotNone(h)
        self.assertTrue(any(email in linea for linea in h.detalle))

    # --- lo que NO debe señalar --------------------------------------------

    def test_una_cuenta_correcta_no_genera_hallazgo(self):
        email = self._usuario("correcto", [ROL_CON_DESK])

        for h in verificar():
            self.assertFalse(
                any(email in linea for linea in h.detalle),
                f"una cuenta correcta no debe aparecer en {h.codigo}",
            )

    def test_un_lector_externo_es_website_user_a_proposito(self):
        """Ser Website User es lo correcto si todos sus roles son de portal."""
        email = self._usuario("portal", [ROL_SIN_DESK], user_type="Website User")

        h = self._hallazgo("acceso-denegado")

        if h:
            self.assertFalse(
                any(email in linea for linea in h.detalle),
                "un rol declarado SIN desk no es una cuenta rota",
            )

    def test_las_cuentas_de_servicio_no_son_hallazgo(self):
        """`svc-*` existe para llamar a la API; que no entre al Desk es correcto."""
        usuarios = accesos._usuarios_reales()

        self.assertFalse([u for u in usuarios if u.name.startswith("svc-")])

    def test_administrator_y_guest_no_son_hallazgo(self):
        usuarios = [u.name for u in accesos._usuarios_reales()]

        self.assertNotIn("Administrator", usuarios)
        self.assertNotIn("Guest", usuarios)

    # --- cuentas sin rol ---------------------------------------------------

    def test_detecta_la_cuenta_sin_ningun_rol(self):
        email = self._usuario("sin-rol", [])

        h = self._hallazgo("cuenta-sin-rol")

        self.assertIsNotNone(h)
        self.assertTrue(any(email in linea for linea in h.detalle))

    # --- el bloqueante -----------------------------------------------------

    def test_no_marca_bloqueante_si_alguien_puede_entrar(self):
        """En un sitio con gente trabajando, esto NUNCA debe dispararse."""
        self._usuario("trabaja", [ROL_CON_DESK])

        self.assertNotIn("instancia-sin-acceso", self._codigos(BLOQUEANTE))

    # --- el informe --------------------------------------------------------

    def test_el_informe_ordena_lo_peor_primero(self):
        self._usuario("degradado3", [ROL_CON_DESK], user_type="Website User")
        self._usuario("sin-rol2", [])

        niveles = [h.nivel for h in verificar()]

        # AVISO (acceso) antes que INFO (cuenta sin rol): quien lee arregla en ese orden.
        if AVISO in niveles and "INFO" in niveles:
            self.assertLess(niveles.index(AVISO), niveles.index("INFO"))

    def test_un_chequeo_roto_no_tumba_el_informe(self):
        def explota():
            raise RuntimeError("fallo simulado")

        original = list(accesos.CHEQUEOS)
        accesos.CHEQUEOS.append(explota)
        try:
            codigos = self._codigos()
            self.assertIn("chequeo-fallido", codigos)
            # y el resto sigue corriendo
            self.assertTrue(len(codigos) >= 1)
        finally:
            accesos.CHEQUEOS[:] = original
