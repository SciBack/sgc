# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Estado de la instancia (#53): qué devuelve, a quién, y que no se cae cuando algo falla.

Todo lo que se monta en la base se deshace al terminar cada test.
"""

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

import sgc
from sgc import estado

USUARIO_SIN_ROL = "estado-sin-rol@example.com"


def _claves(respuesta):
    """Todas las claves de la respuesta, en dos niveles."""
    return {(bloque, clave) for bloque, datos in respuesta.items() for clave in datos}


def _permitidas():
    return {(bloque, clave) for bloque, claves in estado.CAMPOS.items() for clave in claves}


class IntegrationTestComposicion(IntegrationTestCase):
    def test_devuelve_los_cinco_bloques_y_solo_lo_declarado(self):
        respuesta = estado.componer()
        self.assertEqual(set(respuesta), set(estado.CAMPOS))
        for bloque, datos in respuesta.items():
            with self.subTest(bloque=bloque):
                self.assertNotIn("estado", datos, f"el bloque «{bloque}» falló en una instancia sana")
                self.assertEqual(set(datos), estado.CAMPOS[bloque])

    def test_la_version_es_la_del_codigo(self):
        """Criterio 5: coincide con sgc/__init__.py, que es lo que se publica como tag (#52)."""
        respuesta = estado.componer()
        self.assertEqual(respuesta["version"]["sgc"], sgc.__version__)
        self.assertEqual(respuesta["version"]["frappe"], frappe.__version__)

    def test_migracion_pendiente_si_el_codigo_no_es_lo_migrado(self):
        with patch.object(sgc, "__version__", "99.0.0"):
            migracion = estado.componer()["migracion"]
        self.assertTrue(migracion["pendiente"])
        self.assertNotEqual(migracion["version_sgc"], "99.0.0")


class IntegrationTestSubsistemaCaido(IntegrationTestCase):
    """Criterio 6: informa de lo que está mal, no falla por ello."""

    def test_scheduler_parado_se_informa(self):
        parado = {"alerta": True, "scheduler_apagado": True, "horas_desde_ultima": 120.5}
        with patch("sgc.latido.comprobar", return_value=parado):
            scheduler = estado.componer()["scheduler"]
        self.assertEqual(scheduler, {"ok": False, "apagado": True, "horas_desde_ultima": 120.5})

    def test_un_bloque_que_lanza_no_tumba_a_los_demas(self):
        error = RuntimeError("/home/frappe/frappe-bench/sites/secreto: conexión rechazada")
        with patch("sgc.latido.comprobar", side_effect=error):
            respuesta = estado.componer()
        self.assertEqual(respuesta["scheduler"], {"estado": estado.ERROR, "tipo": "RuntimeError"})
        self.assertEqual(respuesta["version"]["sgc"], sgc.__version__)
        self.assertIn("configurado", respuesta["correo"])
        # Del error solo sale el tipo: el mensaje puede llevar rutas.
        self.assertNotIn("/home", json.dumps(respuesta, default=str))

    def test_correo_sin_cuenta_saliente_se_informa(self):
        frappe.db.savepoint("estado_correo")
        try:
            for cuenta in frappe.get_all("Email Account", filters={"default_outgoing": 1}, pluck="name"):
                frappe.db.set_value("Email Account", cuenta, "default_outgoing", 0)
            with patch.dict(frappe.local.conf, {"mail_server": None, "mute_emails": 1}):
                correo = estado.componer()["correo"]
        finally:
            frappe.db.rollback(save_point="estado_correo")
        self.assertFalse(correo["configurado"])
        self.assertTrue(correo["silenciado"])
        self.assertIn(correo["modo"], ("Ensayo", "Real"))

    def test_sin_sso_se_informa(self):
        frappe.db.savepoint("estado_sso")
        try:
            for clave in frappe.get_all("Social Login Key", filters={"enable_social_login": 1}, pluck="name"):
                frappe.db.set_value("Social Login Key", clave, "enable_social_login", 0)
            sso = estado.componer()["sso"]
        finally:
            frappe.db.rollback(save_point="estado_sso")
        self.assertEqual(sso, {"configurado": False})


class IntegrationTestPermisos(IntegrationTestCase):
    def setUp(self):
        self.previo = frappe.session.user
        if not frappe.db.exists("User", USUARIO_SIN_ROL):
            frappe.get_doc(
                {"doctype": "User", "email": USUARIO_SIN_ROL, "first_name": "Sin rol", "send_welcome_email": 0}
            ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user(self.previo)

    def test_system_manager_obtiene_el_estado(self):
        frappe.set_user("Administrator")
        self.assertEqual(set(estado.instancia()), set(estado.CAMPOS))

    def test_usuario_sin_rol_de_administracion_no(self):
        frappe.set_user(USUARIO_SIN_ROL)
        with self.assertRaises(frappe.PermissionError):
            estado.instancia()

    def test_anonimo_no_llega_a_ejecutarlo(self):
        """Criterio 3: sin sesión, Frappe corta en la lista blanca de métodos, antes del código."""
        frappe.set_user("Guest")
        self.assertNotIn(estado.instancia, frappe.guest_methods)
        with self.assertRaises(frappe.PermissionError):
            frappe.is_whitelisted(estado.instancia)


class IntegrationTestListaBlanca(IntegrationTestCase):
    def test_nada_fuera_de_la_lista_aunque_un_bloque_devuelva_de_mas(self):
        def sso_indiscreto():
            return {"configurado": True, "usuarios": ["alguien@example.com"], "secreto": "x"}

        with patch.dict(estado.BLOQUES, {"sso": sso_indiscreto}):
            respuesta = estado.componer()
        self.assertEqual(respuesta["sso"], {"configurado": True})
        self.assertTrue(_claves(respuesta) <= _permitidas())

    def test_sin_identificadores_de_personas_ni_rutas(self):
        texto = json.dumps(estado.componer(), default=str)
        self.assertNotIn("@", texto)
        self.assertNotIn("/", texto)
