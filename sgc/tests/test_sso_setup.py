"""SSO configurado desde el despliegue (#46): `sgc.setup.f3b_sso`.

Usa proveedores de prueba (`sgc_prueba_*`) para no tocar nunca un registro real: el lab es
una copia de producción y trae su propio `keycloak`, que estos tests no deben alterar.
"""

import contextlib
import io
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f3b_sso

ISSUER = "https://idp.example.org/realms/prueba"
SECRETO = "secreto-de-prueba-que-no-debe-salir-en-logs"


def _conf(**extra):
    base = {"sgc_sso_issuer": ISSUER, "sgc_sso_client_id": "sgc-prueba",
            "sgc_sso_client_secret": SECRETO, "sgc_sso_proveedor": "sgc_prueba_a",
            "sgc_sso_etiqueta": "Cuenta de prueba"}
    base.update(extra)
    return {k: v for k, v in base.items() if v is not None}


class TestComposicion(IntegrationTestCase):
    def test_keycloak_usa_el_callback_nativo_y_el_issuer_como_base(self):
        cfg = f3b_sso.leer(_conf(sgc_sso_issuer=ISSUER + "/", sgc_sso_proveedor="keycloak"))
        campos = f3b_sso.componer(cfg)
        self.assertEqual(campos["base_url"], ISSUER)  # sin barra final
        self.assertEqual(campos["redirect_url"], f3b_sso.NATIVOS["keycloak"])
        self.assertEqual(campos["authorize_url"], "/protocol/openid-connect/auth")

    def test_otro_proveedor_usa_el_callback_generico(self):
        campos = f3b_sso.componer(f3b_sso.leer(_conf(sgc_sso_proveedor="mi_idp")))
        self.assertEqual(campos["redirect_url"], "/api/method/frappe.integrations.oauth2_logins.custom/mi_idp")

    def test_las_rutas_se_pueden_declarar(self):
        rutas = {"autorizacion": "/oauth2/authorize", "token": "/oauth2/token", "usuario": "/oauth2/userinfo"}
        campos = f3b_sso.componer(f3b_sso.leer(_conf(sgc_sso_rutas=rutas)))
        self.assertEqual((campos["authorize_url"], campos["access_token_url"], campos["api_endpoint"]),
                         ("/oauth2/authorize", "/oauth2/token", "/oauth2/userinfo"))

    def test_la_configuracion_invalida_se_explica(self):
        for conf in (_conf(sgc_sso_issuer="http://inseguro.example.org"), _conf(sgc_sso_client_id=None),
                     _conf(sgc_sso_proveedor="Con Mayúsculas")):
            with self.assertRaises(f3b_sso.ConfiguracionInvalida):
                f3b_sso.leer(conf)


class IntegrationTestSsoDesdeSiteConfig(IntegrationTestCase):
    def setUp(self):
        self._gestionado = frappe.db.get_default(f3b_sso.CLAVE_GESTIONADO)
        self.addCleanup(self._limpiar)

    def _limpiar(self):
        for nombre in ("sgc_prueba_a", "sgc_prueba_b", "sgc_prueba_manual"):
            if frappe.db.exists("Social Login Key", nombre):
                frappe.delete_doc("Social Login Key", nombre, ignore_permissions=True, force=True)
        frappe.db.set_default(f3b_sso.CLAVE_GESTIONADO, self._gestionado)
        frappe.db.commit()

    def _run(self, conf):
        sin_sso = {k: None for k in frappe.local.conf if k.startswith("sgc_sso_")}
        salida = io.StringIO()
        with patch.dict(frappe.local.conf, {**sin_sso, **conf}), contextlib.redirect_stdout(salida):
            for k in [k for k in frappe.local.conf if k.startswith("sgc_sso_") and frappe.local.conf[k] is None]:
                frappe.local.conf.pop(k)
            resultado = f3b_sso.run()
        return resultado, salida.getvalue()

    def test_sin_configuracion_no_crea_nada_y_lo_dice(self):
        antes = frappe.db.count("Social Login Key")
        resultado, salida = self._run({})
        self.assertEqual(resultado, "sin-configurar")
        self.assertIn("no configurado", salida)
        self.assertEqual(frappe.db.count("Social Login Key"), antes)

    def test_configuracion_incompleta_no_falla_el_migrate(self):
        resultado, salida = self._run(_conf(sgc_sso_client_id=None))
        self.assertEqual(resultado, "invalida")
        self.assertIn("sgc_sso_client_id", salida)
        self.assertFalse(frappe.db.exists("Social Login Key", "sgc_prueba_a"))

    def test_crea_el_registro_con_su_etiqueta_y_sin_mostrar_el_secreto(self):
        resultado, salida = self._run(_conf())
        self.assertEqual(resultado, "creado")
        doc = frappe.get_doc("Social Login Key", "sgc_prueba_a")
        self.assertEqual((doc.provider_name, doc.base_url, doc.client_id, doc.enable_social_login),
                         ("Cuenta de prueba", ISSUER, "sgc-prueba", 1))
        self.assertEqual(doc.get_password("client_secret"), SECRETO)
        self.assertNotIn(SECRETO, salida)

    def test_reejecutar_no_duplica_ni_altera(self):
        self._run(_conf())
        modificado = frappe.db.get_value("Social Login Key", "sgc_prueba_a", "modified")
        resultado, _ = self._run(_conf())
        self.assertEqual(resultado, "sin cambios")
        self.assertEqual(frappe.db.get_value("Social Login Key", "sgc_prueba_a", "modified"), modificado)
        self.assertEqual(frappe.db.count("Social Login Key", {"name": ["like", "sgc_prueba_%"]}), 1)

    def test_sin_secreto_declarado_se_conserva_el_guardado(self):
        self._run(_conf())
        resultado, _ = self._run(_conf(sgc_sso_client_secret=None, sgc_sso_etiqueta="Otra etiqueta"))
        self.assertEqual(resultado, "actualizado")
        doc = frappe.get_doc("Social Login Key", "sgc_prueba_a")
        self.assertEqual((doc.provider_name, doc.get_password("client_secret")), ("Otra etiqueta", SECRETO))

    def test_cambiar_de_proveedor_no_deja_residuos(self):
        self._run(_conf())
        resultado, salida = self._run(_conf(sgc_sso_proveedor="sgc_prueba_b"))
        self.assertEqual(resultado, "creado")
        self.assertFalse(frappe.db.exists("Social Login Key", "sgc_prueba_a"))
        self.assertTrue(frappe.db.exists("Social Login Key", "sgc_prueba_b"))
        self.assertIn("retirado el anterior «sgc_prueba_a»", salida)

    def test_un_registro_creado_a_mano_nunca_se_toca(self):
        manual = frappe.new_doc("Social Login Key")
        manual.provider_name = "sgc_prueba_manual"
        manual.update(f3b_sso.componer(f3b_sso.leer(_conf(sgc_sso_proveedor="sgc_prueba_manual"))))
        manual.client_secret = SECRETO
        manual.insert(ignore_permissions=True)
        self._run(_conf())
        self._run(_conf(sgc_sso_proveedor="sgc_prueba_b"))
        self.assertTrue(frappe.db.exists("Social Login Key", "sgc_prueba_manual"))
