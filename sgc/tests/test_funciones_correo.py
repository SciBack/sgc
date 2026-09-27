# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Funciones de correo (#92).

  Envío de documentos y fichas
    - solo lo publicado, solo quien gobierna la documentación, direcciones válidas
    - en ensayo no sale nada y queda anotado; en real sale con el archivo
    - un documento de solo consulta sale sin archivo; la ficha para externos, en
      formato público
  Aviso de medición
    - la ficha calcula el día del aviso; la próxima medición avanza al registrar
      un valor, y no retrocede; la regla encuentra la ficha ese día
  Comunicados
    - mantenimiento con antelación y fin posterior al inicio
    - enviar sella, cierra y no se repite

El envío real se sustituye por un doble (`_make`): el CI no tiene cuenta de correo.
Todo se deshace al final de cada test (rollback de `IntegrationTestCase`).
"""

import io
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_months, add_to_date, getdate, now_datetime, nowdate

from sgc import correo, envio
from sgc.sgc_estructura.doctype.ficha_indicador.ficha_indicador import fecha_aviso
from sgc.tests import factories

DISTRIBUYE = "sgc-prueba-envio-dpgc@example.com"
LECTOR = "sgc-prueba-envio-lector@example.com"
MAKE = "frappe.core.doctype.communication.email._make"


def _usuario(correo_, *roles):
    if frappe.db.exists("User", correo_):
        return
    u = frappe.get_doc({"doctype": "User", "email": correo_, "first_name": correo_.split("@")[0],
                        "send_welcome_email": 0})
    for rol in roles:
        u.append("roles", {"role": rol})
    u.insert(ignore_permissions=True)


def _pdf():
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    salida = io.BytesIO()
    w.write(salida)
    return salida.getvalue()


def _modo(modo, lista=""):
    cfg = frappe.get_single("Configuracion Correo")
    cfg.modo = modo
    cfg.lista_blanca = lista
    cfg.save(ignore_permissions=True)


class _Base(IntegrationTestCase):
    def setUp(self):
        _usuario(DISTRIBUYE, "DPGC")
        _usuario(LECTOR, "Decano/Director (lectura)")
        factories.desactivar_workflow("Documento Controlado")
        _modo(correo.ENSAYO)

    def tearDown(self):
        frappe.set_user("Administrator")

    def _como(self, usuario):
        frappe.set_user(usuario)
        self.addCleanup(frappe.set_user, "Administrator")

    def _documento(self, publicado=True, solo_consulta=0, con_archivo=True):
        doc = factories.crear_documento_controlado()
        if con_archivo:
            f = frappe.get_doc({"doctype": "File", "file_name": "procedimiento.pdf", "content": _pdf(),
                                "is_private": 1, "attached_to_doctype": "Documento Controlado",
                                "attached_to_name": doc.name, "attached_to_field": "archivo"}
                               ).insert(ignore_permissions=True)
            frappe.db.set_value("Documento Controlado", doc.name, "archivo", f.file_url, update_modified=False)
        frappe.db.set_value("Documento Controlado", doc.name, {
            "estado": "Publicado" if publicado else "Borrador", "solo_consulta": solo_consulta,
        }, update_modified=False)
        return frappe.get_doc("Documento Controlado", doc.name)


class IntegrationTestEnvioDocumentos(_Base):
    def test_solo_se_envia_lo_publicado(self):
        doc = self._documento(publicado=False)
        self._como(DISTRIBUYE)
        with self.assertRaises(frappe.ValidationError) as ctx:
            envio.enviar_por_correo(doc.doctype, doc.name, externos="alguien@example.org")
        self.assertIn("publicado", str(ctx.exception))

    def test_quien_solo_lee_no_envia(self):
        doc = self._documento()
        self._como(LECTOR)
        with self.assertRaises(frappe.PermissionError):
            envio.enviar_por_correo(doc.doctype, doc.name, externos="alguien@example.org")

    def test_una_direccion_no_valida_se_rechaza_y_se_nombra(self):
        doc = self._documento()
        self._como(DISTRIBUYE)
        with self.assertRaises(frappe.ValidationError) as ctx:
            envio.enviar_por_correo(doc.doctype, doc.name, externos="bien@example.org, mal-escrita")
        self.assertIn("mal-escrita", str(ctx.exception))

    def test_hay_un_tope_de_destinatarios(self):
        doc = self._documento()
        self._como(DISTRIBUYE)
        muchos = ",".join(f"p{i}@example.org" for i in range(envio.MAX_DESTINATARIOS + 1))
        with self.assertRaises(frappe.ValidationError):
            envio.enviar_por_correo(doc.doctype, doc.name, externos=muchos)

    def test_en_ensayo_no_sale_nada_y_queda_anotado(self):
        doc = self._documento()
        self._como(DISTRIBUYE)
        with patch(MAKE) as make:
            res = envio.enviar_por_correo(doc.doctype, doc.name, usuarios=[LECTOR],
                                          externos="externo@example.org")
        make.assert_not_called()
        self.assertEqual(res["enviados"], [])
        anotados = frappe.get_all("Registro Correo", filters={"documento": doc.name},
                                  fields=["destinatario", "resultado", "aviso"])
        self.assertEqual({a.destinatario for a in anotados}, {LECTOR, "externo@example.org"})
        self.assertTrue(all(a.resultado == correo.NO_ENVIADO and a.aviso == "Envío manual" for a in anotados))

    def test_en_real_sale_con_el_archivo(self):
        _modo(correo.REAL)
        doc = self._documento()
        self._como(DISTRIBUYE)
        with patch(MAKE) as make:
            res = envio.enviar_por_correo(doc.doctype, doc.name, externos="externo@example.org")
        self.assertEqual(res["enviados"], ["externo@example.org"])
        kwargs = make.call_args.kwargs
        self.assertEqual((kwargs["doctype"], kwargs["name"]), (doc.doctype, doc.name))
        self.assertEqual(len(kwargs["attachments"]), 1)

    def test_la_lista_blanca_retiene_lo_demas(self):
        _modo(correo.REAL, "permitido@example.org")
        doc = self._documento()
        self._como(DISTRIBUYE)
        with patch(MAKE) as make:
            res = envio.enviar_por_correo(doc.doctype, doc.name,
                                          externos="permitido@example.org, otro@example.org")
        self.assertEqual(make.call_args.kwargs["recipients"], ["permitido@example.org"])
        self.assertEqual(res["retenidos"], [("otro@example.org", correo.OMITIDO)])

    def test_un_documento_de_solo_consulta_sale_sin_archivo(self):
        _modo(correo.REAL)
        doc = self._documento(solo_consulta=1)
        self._como(DISTRIBUYE)
        with patch(MAKE) as make:
            envio.enviar_por_correo(doc.doctype, doc.name, externos="externo@example.org")
        kwargs = make.call_args.kwargs
        self.assertFalse(kwargs["attachments"])
        self.assertIn("solo consulta", kwargs["content"])


class IntegrationTestEnvioFichas(_Base):
    def _ficha(self):
        proceso = factories.crear_proceso(prefijo="ENV").name
        ficha = frappe.get_doc({"doctype": envio.FICHA, "proceso": proceso}).insert(ignore_permissions=True)
        frappe.db.set_value(envio.FICHA, ficha.name, "estado", "Publicado", update_modified=False)
        return ficha

    def test_para_externos_va_en_formato_publico(self):
        _modo(correo.REAL)
        ficha = self._ficha()
        self._como(DISTRIBUYE)
        with patch(MAKE) as make:
            res = envio.enviar_por_correo(envio.FICHA, ficha.name, externos="consultor@example.org")
        if frappe.db.exists("Print Format", envio.FORMATO_FICHA_PUBLICO):
            self.assertEqual(res["formato"], envio.FORMATO_FICHA_PUBLICO)
            self.assertEqual(make.call_args.kwargs["print_format"], envio.FORMATO_FICHA_PUBLICO)

    def test_entre_usuarios_va_en_formato_interno(self):
        _modo(correo.REAL)
        ficha = self._ficha()
        self._como(DISTRIBUYE)
        with patch(MAKE):
            res = envio.enviar_por_correo(envio.FICHA, ficha.name, usuarios=[LECTOR])
        if frappe.db.exists("Print Format", envio.FORMATO_FICHA):
            self.assertEqual(res["formato"], envio.FORMATO_FICHA)


class IntegrationTestAvisoMedicion(_Base):
    def _ficha(self, frecuencia="trimestral", **extra):
        ind = factories.crear_indicador(prefijo="MED").name
        return frappe.get_doc({"doctype": "Ficha Indicador", "indicador": ind, "frecuencia": frecuencia,
                               "responsable": DISTRIBUYE, **extra}).insert(ignore_permissions=True)

    def test_la_ficha_calcula_el_dia_del_aviso(self):
        ficha = self._ficha(proxima_medicion=add_days(nowdate(), 20), dias_aviso=5)
        self.assertEqual(getdate(ficha.fecha_aviso_medicion), getdate(add_days(nowdate(), 15)))

    def test_dias_de_aviso_negativos_se_rechazan(self):
        with self.assertRaises(frappe.ValidationError):
            self._ficha(dias_aviso=-1)

    def test_registrar_un_valor_avanza_la_proxima_medicion(self):
        ficha = self._ficha()
        frappe.get_doc({"doctype": "Valor Indicador", "indicador": ficha.indicador, "valor_num": 80,
                        "fecha": "2026-03-15 10:00:00"}).insert(ignore_permissions=True)
        ficha.reload()
        self.assertEqual(getdate(ficha.proxima_medicion), getdate(add_months("2026-03-15", 3)))
        self.assertEqual(getdate(ficha.fecha_aviso_medicion), getdate(fecha_aviso(ficha.proxima_medicion, 7)))

    def test_una_medicion_atrasada_no_hace_retroceder_el_calendario(self):
        ficha = self._ficha(proxima_medicion="2026-12-31")
        frappe.get_doc({"doctype": "Valor Indicador", "indicador": ficha.indicador, "valor_num": 80,
                        "fecha": "2026-01-10 10:00:00"}).insert(ignore_permissions=True)
        ficha.reload()
        self.assertEqual(str(ficha.proxima_medicion), "2026-12-31")

    def test_la_regla_encuentra_la_ficha_el_dia_del_aviso(self):
        regla = "SGC - Medicion de indicador proxima"
        if not frappe.db.exists("Notification", regla):
            self.skipTest("f7 no aplicado en este sitio")
        ficha = self._ficha(proxima_medicion=add_days(nowdate(), 7), dias_aviso=7)
        hoy = [d.name for d in frappe.get_doc("Notification", regla).get_documents_for_today()]
        self.assertIn(ficha.name, hoy)


class IntegrationTestComunicado(_Base):
    def _comunicado(self, **extra):
        vals = {"doctype": "Comunicado", "asunto": "Nuevo informe de salidas no conformes",
                "tipo": "Nueva funcionalidad", "mensaje": "<p>Ya está disponible.</p>",
                "roles": [{"rol": "Decano/Director (lectura)"}]}
        vals.update(extra)
        return frappe.get_doc(vals).insert(ignore_permissions=True)

    def test_un_mantenimiento_sin_antelacion_no_se_envia(self):
        c = self._comunicado(tipo="Mantenimiento programado",
                             inicio_mantenimiento=add_to_date(now_datetime(), hours=2))
        with self.assertRaises(frappe.ValidationError) as ctx:
            c.enviar()
        self.assertIn("antelación", str(ctx.exception))

    def test_el_fin_va_despues_del_inicio(self):
        inicio = add_to_date(now_datetime(), days=3)
        with self.assertRaises(frappe.ValidationError):
            self._comunicado(tipo="Mantenimiento programado", inicio_mantenimiento=inicio,
                             fin_mantenimiento=add_to_date(inicio, hours=-1))

    def test_enviar_sella_cierra_y_no_se_repite(self):
        c = self._comunicado()
        self._como(DISTRIBUYE)
        res = c.enviar()
        c.reload()
        self.assertEqual(c.estado, "Enviado")
        self.assertEqual(c.enviado_por, DISTRIBUYE)
        self.assertEqual(res["enviados"], 0)  # modo ensayo: nada sale...
        self.assertGreaterEqual(c.n_retenidos, 1)  # ...y consta que habría salido
        with self.assertRaises(frappe.ValidationError):
            c.enviar()
        c.asunto = "Otro asunto"
        with self.assertRaises(frappe.ValidationError):
            c.save(ignore_permissions=True)

    def test_un_mantenimiento_con_antelacion_se_envia(self):
        c = self._comunicado(tipo="Mantenimiento programado",
                             inicio_mantenimiento=add_to_date(now_datetime(), days=3))
        c.enviar()
        self.assertEqual(frappe.db.get_value("Comunicado", c.name, "estado"), "Enviado")

    def test_sin_usuarios_en_los_roles_no_se_envia(self):
        rol = "_SGC Rol Sin Usuarios"
        if not frappe.db.exists("Role", rol):
            frappe.get_doc({"doctype": "Role", "role_name": rol}).insert(ignore_permissions=True)
        c = self._comunicado(roles=[{"rol": rol}])
        with self.assertRaises(frappe.ValidationError):
            c.enviar()
