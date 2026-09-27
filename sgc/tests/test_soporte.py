# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Canal de soporte (#56): reportar un problema desde el sistema.

  Qué viaja
    - la pantalla, sin el identificador del registro (nunca un correo ajeno)
    - el contexto técnico es exactamente la lista blanca, sin roles automáticos
    - lo que se previsualiza es lo que se envía
  Sin configuración
    - el menú no se activa y los métodos se niegan
  Zammad
    - crea el ticket a nombre de quien reporta, con su prioridad y el token
    - caído o con error: mensaje claro, alternativa y el texto para copiar
  Correo
    - pasa por el modo y la lista blanca; retenido es «no enviado»
  Configuración
    - no se activa a medias ni con una URL sin https

Las llamadas HTTP y el envío de correo se sustituyen por dobles: el CI no tiene
helpdesk ni cuenta de correo.
"""

from unittest.mock import MagicMock, patch

import frappe
import requests
from frappe.tests import IntegrationTestCase

from sgc import hooks, soporte

POST = "sgc.soporte.requests.post"
MAKE = "frappe.core.doctype.communication.email._make"
SOPORTE = "soporte@sgc-prueba.example.com"


def _canal(activo=1, proveedor="Zammad", **extra):
    c = frappe.get_single("Configuracion Soporte")
    valores = {
        "activo": activo,
        "proveedor": proveedor,
        "correo_soporte": SOPORTE,
        "zammad_url": "https://soporte.sgc-prueba.example.com",
        "zammad_token": "token-de-prueba",
        "zammad_grupo": "SGC",
        "prioridad_baja": "1 low",
        "prioridad_media": "2 normal",
        "prioridad_alta": "3 high",
        "tiempo_espera": 5,
    }
    valores.update(extra)
    c.update(valores)
    c.save(ignore_permissions=True)
    return c


def _correo(modo, lista=""):
    cfg = frappe.get_single("Configuracion Correo")
    cfg.modo = modo
    cfg.lista_blanca = lista
    cfg.save(ignore_permissions=True)


def _respuesta(status, datos=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = datos or {}
    return r


class _Base(IntegrationTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")


class IntegrationTestSoporteQueViaja(_Base):
    def test_la_pantalla_nunca_lleva_el_registro(self):
        casos = {
            "/desk/no-conformidad/NC-2026-00015": "no-conformidad (un registro)",
            "/desk/user/persona@example.com": "user (un registro)",
            "/desk/no-conformidad": "no-conformidad",
            "/desk/no-conformidad/view/report": "no-conformidad (vista)",
            "/desk/evento-riesgo/new-evento-riesgo-abc": "evento-riesgo (nuevo registro)",
            "/desk/query-report/Matriz%20de%20Riesgos": "Informe: Matriz de Riesgos",
            "/desk": "Inicio",
            "": "Inicio",
            "/desk/sgc?x=persona@example.com": "sgc",
        }
        for ruta, esperado in casos.items():
            with self.subTest(ruta=ruta):
                self.assertEqual(soporte.pantalla(ruta), esperado)

    def test_el_contexto_es_la_lista_blanca(self):
        ctx = soporte.contexto("/desk/user/persona@example.com")
        self.assertEqual(tuple(ctx), soporte.CAMPOS_CONTEXTO)
        self.assertEqual(ctx["Usuario"], "Administrator")
        self.assertEqual(ctx["Versión Frappe"], frappe.__version__)
        for automatico in ("All", "Guest", "Desk User"):
            self.assertNotIn(automatico, ctx["Roles"].split(", "))
        self.assertNotIn("persona@example.com", str(ctx))

    def test_lo_que_se_previsualiza_es_lo_que_se_envia(self):
        _canal()
        vista = soporte.previsualizar("No abre el informe", "Al abrirlo sale en blanco.", "Alta",
                                      "/desk/no-conformidad/NC-2026-00015")
        with patch(POST, return_value=_respuesta(201, {"number": "22019"})) as post:
            soporte.reportar("No abre el informe", "Al abrirlo sale en blanco.", "Alta",
                             "/desk/no-conformidad/NC-2026-00015")
        articulo = post.call_args.kwargs["json"]["article"]
        self.assertEqual(articulo["body"], vista["cuerpo"])
        self.assertNotIn("NC-2026-00015", articulo["body"])

    def test_valida_lo_que_escribe(self):
        for asunto, descripcion, prioridad in (("", "x", "Media"), ("x", " ", "Media"),
                                               ("x" * 141, "x", "Media"), ("x", "x", "Urgentísima")):
            with self.subTest(asunto=asunto[:10], prioridad=prioridad):
                with self.assertRaises(frappe.ValidationError):
                    soporte.componer(asunto, descripcion, prioridad)


class IntegrationTestSoporteSinCanal(_Base):
    def test_sin_canal_no_hay_menu_ni_envio(self):
        _canal(activo=0)
        self.assertFalse(soporte.estado()["activo"])
        boot = frappe._dict()
        soporte.boot(boot)
        self.assertFalse(boot.sgc_soporte["activo"])
        with patch(POST) as post:
            for metodo in (soporte.previsualizar, soporte.reportar):
                with self.subTest(metodo=metodo.__name__):
                    with self.assertRaises(frappe.ValidationError):
                        metodo("a", "b", "Media")
            post.assert_not_called()

    def test_el_menu_depende_del_canal(self):
        item = next(i for i in hooks.standard_help_items if i["item_label"] == "Reportar un problema")
        self.assertIn("sgc_soporte.activo", item["condition"])
        self.assertIn("sgc.soporte.boot", hooks.extend_bootinfo)

    def test_el_estado_no_lleva_secretos(self):
        _canal()
        self.assertEqual(set(soporte.estado()), {"activo", "alternativa"})


class IntegrationTestSoporteZammad(_Base):
    def test_crea_el_ticket_a_nombre_de_quien_reporta(self):
        _canal()
        with patch(POST, return_value=_respuesta(201, {"id": 19, "number": "22019"})) as post:
            r = soporte.reportar("No abre el informe", "Sale en blanco.", "Baja", "/desk/sgc")
        self.assertEqual(r, {"ok": True, "referencia": "22019", "proveedor": "Zammad"})
        args = post.call_args
        self.assertEqual(args.args[0], "https://soporte.sgc-prueba.example.com/api/v1/tickets")
        self.assertEqual(args.kwargs["headers"]["Authorization"], "Token token=token-de-prueba")
        self.assertEqual(args.kwargs["timeout"], 5)
        carga = args.kwargs["json"]
        correo = frappe.db.get_value("User", "Administrator", "email")
        self.assertEqual(carga["customer_id"], f"guess:{correo}")
        self.assertEqual(carga["group"], "SGC")
        self.assertEqual(carga["priority"], "1 low")
        self.assertEqual(carga["article"]["sender"], "Customer")
        self.assertFalse(carga["article"]["internal"])

    def test_caido_ofrece_la_alternativa_y_el_texto(self):
        _canal()
        for efecto in (requests.ConnectionError("sin red"), requests.Timeout("lento")):
            with self.subTest(efecto=type(efecto).__name__):
                with patch(POST, side_effect=efecto):
                    r = soporte.reportar("No abre el informe", "Sale en blanco.", "Media", "/desk/sgc")
                self.assertFalse(r["ok"])
                self.assertEqual(r["alternativa"], SOPORTE)
                self.assertIn("No abre el informe", r["texto"])
                self.assertIn("Sale en blanco.", r["texto"])

    def test_un_error_del_helpdesk_tampoco_es_un_error_generico(self):
        _canal()
        with patch(POST, return_value=_respuesta(422, {"error": "Group not found"})):
            r = soporte.reportar("No abre", "Sale en blanco.", "Media", "/desk/sgc")
        self.assertFalse(r["ok"])
        self.assertTrue(r["mensaje"])


class IntegrationTestSoporteCorreo(_Base):
    def test_sale_por_correo_y_pasa_por_la_lista_blanca(self):
        _canal(proveedor="Correo")
        _correo("Real")
        with patch(MAKE) as make:
            r = soporte.reportar("No abre", "Sale en blanco.", "Alta", "/desk/sgc")
        self.assertTrue(r["ok"])
        self.assertEqual(make.call_args.kwargs["recipients"], [SOPORTE])
        self.assertIn("[Alta] No abre", make.call_args.kwargs["subject"])

        _correo("Real", "otra-persona@sgc-prueba.example.com")
        with patch(MAKE) as make:
            r = soporte.reportar("No abre", "Sale en blanco.", "Alta", "/desk/sgc")
        make.assert_not_called()
        self.assertFalse(r["ok"])


class IntegrationTestConfiguracionSoporte(_Base):
    def test_no_se_activa_a_medias(self):
        with self.assertRaises(frappe.ValidationError):
            _canal(zammad_grupo="")
        with self.assertRaises(frappe.ValidationError):
            _canal(zammad_url="http://soporte.sgc-prueba.example.com")
        with self.assertRaises(frappe.ValidationError):
            _canal(proveedor="Correo", correo_soporte="")

    def test_apagado_no_exige_nada(self):
        _canal(activo=0, zammad_grupo="", zammad_url="", correo_soporte="")
        self.assertFalse(frappe.db.get_single_value("Configuracion Soporte", "activo"))
