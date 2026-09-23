# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Avisos por correo en las transiciones de estado (#29).

Dos niveles:

- **A quién va cada aviso.** Para cada regla de `f15`, un documento EN MEMORIA
  en cada estado de llegada, y los destinatarios que Frappe resuelve con
  `get_list_of_recipients`, el mismo método que usa al enviar. No hace falta
  recorrer el workflow para saber a quién escribe una regla, y así cada estado
  se prueba sin arrastrar las validaciones de los anteriores.
- **Que el correo sale una vez, y solo en una transición real.** Con una No
  Conformidad de verdad: guardar sin cambiar el estado no envía, el modo de
  ensayo no envía, y un SMTP caído no impide guardar.

`frappe.sendmail` se sustituye por un mock en TODO el módulo: el lab es una
copia de producción con la cuenta de correo real, y un aviso a un rol llegaría
a las personas que lo tienen. Lo que se comprueba es a quién se le PIDE enviar.

Los roles de un sitio con datos (el lab) tienen más usuarios que los de la
prueba; por eso se comprueba que el usuario de prueba está o no está, nunca la
lista exacta de un rol.
"""
from unittest.mock import patch

import frappe
from frappe.email.doctype.notification.notification import get_context
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc import correo
from sgc.patches import notificaciones_por_correo
from sgc.setup import f7_notificaciones as f7
from sgc.setup import f15_notificaciones_workflow as f15
from sgc.tests import factories

DOMINIO = "sgc-transicion.example.com"

R_DOC = "SGC - Documento Controlado cambia de estado"
R_PUBLICADO = "SGC - Documento Controlado publicado"
R_NC = "SGC - No Conformidad cambia de estado"
R_ACCION = "SGC - Accion de mejora cambia de estado"
R_AUDITORIA = "SGC - Auditoria cambia de estado"
R_HALLAZGO = "SGC - Hallazgo de auditoria cambia de estado"


def _correo(local):
    return f"{local}@{DOMINIO}"


class IntegrationTestNotificacionesTransicion(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # f15.run() comitea (lo necesita en producción) y deja in_patch=True,
        # que silencia TODAS las notificaciones: hay que apagarlo antes de guardar.
        f15.run()
        frappe.flags.in_patch = False

    def setUp(self):
        self.sendmail = patch("frappe.sendmail").start()
        self.addCleanup(patch.stopall)
        frappe.set_user("Administrator")
        frappe.db.set_single_value("Configuracion Correo", {"modo": correo.REAL, "lista_blanca": ""})

        self.persona = {}
        for local, rol in (
            ("responsable", None),
            ("verificador", None),
            ("elaborador", None),
            ("revisor", None),
            ("aprobador", None),
            ("auditor-equipo", None),
            ("dpgc", "DPGC"),
            ("calidad-programa", "Responsable de Calidad de Programa"),
            ("dueno", "Dueño de Proceso"),
            ("autoridad", "Autoridad Aprobadora"),
            ("auditor", "Auditor Interno"),
        ):
            self.persona[local] = self._usuario(local, rol)

    def tearDown(self):
        frappe.db.rollback()

    # --- helpers -------------------------------------------------------------

    def _usuario(self, local, rol):
        email = _correo(local)
        if not frappe.db.exists("User", email):
            usuario = frappe.get_doc(
                {"doctype": "User", "email": email, "first_name": local, "send_welcome_email": 0}
            )
            if rol:
                usuario.append("roles", {"role": rol})
            usuario.insert(ignore_permissions=True)
        return email

    def _para(self, regla, doc):
        """Los destinatarios «Para» de `regla` sobre `doc`, como los resuelve Frappe."""
        notificacion = frappe.get_doc("Notification", regla)
        para, _cc, _cco = notificacion.get_list_of_recipients(doc, get_context(doc))
        return set(para)

    def _nuestros(self, regla, doc):
        """Solo los usuarios de esta prueba: los roles del lab traen más gente."""
        return {c for c in self._para(regla, doc) if c.endswith("@" + DOMINIO)}

    def _dispara(self, regla, doc):
        notificacion = frappe.get_doc("Notification", regla)
        return bool(frappe.safe_eval(notificacion.condition, None, get_context(doc)))

    def _p(self, *locales):
        return {self.persona[l] for l in locales}

    # --- las reglas quedan declaradas ---------------------------------------

    def test_hay_una_regla_de_correo_con_campana_por_documento(self):
        for regla in (R_DOC, R_PUBLICADO, R_NC, R_ACCION, R_AUDITORIA, R_HALLAZGO):
            n = frappe.db.get_value(
                "Notification",
                regla,
                ["channel", "event", "value_changed", "send_system_notification", "enabled"],
                as_dict=True,
            )
            self.assertIsNotNone(n, regla)
            self.assertEqual(n.channel, "Email", regla)
            self.assertEqual(n.event, "Value Change", regla)
            self.assertEqual(n.value_changed, "estado", regla)
            self.assertEqual(n.send_system_notification, 1, regla)
            self.assertEqual(n.enabled, 1, regla)

    def test_run_es_idempotente(self):
        f15.run()
        frappe.flags.in_patch = False
        nombres = [cfg["name"] for cfg in f15.NOTIFICACIONES]
        self.assertEqual(frappe.db.count("Notification", {"name": ["in", nombres]}), len(nombres))

    # --- Documento Controlado -----------------------------------------------

    def _documento(self, estado, **campos):
        valores = {
            "doctype": "Documento Controlado",
            "name": "DOC-PRUEBA-TRANSICION",
            "codigo": "DOC-PRUEBA-TRANSICION",
            "titulo": "Manual de prueba",
            "estado": estado,
            "elaborado_por": self.persona["elaborador"],
            "revisado_por": self.persona["revisor"],
            "aprobado_por": self.persona["aprobador"],
        }
        valores.update(campos)
        return frappe.get_doc(valores)

    def test_documento_avisa_a_quien_actua_en_cada_estado(self):
        casos = {
            "En revision": {"revisor"},
            "Observado": {"elaborador"},
            "Aprobado": {"aprobador"},
            "Obsoleto": {"elaborador"},
            "Borrador": set(),
        }
        for estado, esperados in casos.items():
            with self.subTest(estado=estado):
                self.assertEqual(self._nuestros(R_DOC, self._documento(estado)), self._p(*esperados))

    def test_documento_sin_persona_nombrada_avisa_al_rol(self):
        casos = {
            ("En revision", "revisado_por"): "dpgc",
            ("Observado", "elaborado_por"): "dueno",
            ("Aprobado", "aprobado_por"): "autoridad",
        }
        for (estado, campo), rol in casos.items():
            with self.subTest(estado=estado):
                doc = self._documento(estado, **{campo: None})
                self.assertIn(self.persona[rol], self._para(R_DOC, doc))

    def test_la_publicacion_va_en_su_regla_con_el_archivo(self):
        doc = self._documento("Publicado", archivo="/private/files/manual-prueba.pdf")

        self.assertFalse(self._dispara(R_DOC, doc))
        self.assertTrue(self._dispara(R_PUBLICADO, doc))
        self.assertTrue(self._p("elaborador", "revisor", "aprobador", "dpgc") <= self._para(R_PUBLICADO, doc))
        adjuntos = frappe.get_doc("Notification", R_PUBLICADO).get_attachment(doc)
        self.assertEqual(adjuntos, [{"file_url": "/private/files/manual-prueba.pdf"}])

    # --- No Conformidad y Acción de Mejora -----------------------------------

    def _nc(self, estado, **campos):
        valores = {
            "doctype": "No Conformidad",
            "name": "NC-PRUEBA-TRANSICION",
            "titulo": "NC de prueba",
            "estado": estado,
            "responsable": self.persona["responsable"],
            "verificada_por": self.persona["verificador"],
        }
        valores.update(campos)
        return frappe.get_doc(valores)

    def test_no_conformidad_avisa_a_quien_actua_en_cada_estado(self):
        casos = {
            "En analisis": {"responsable"},
            "En tratamiento": {"responsable"},
            "En verificacion": {"verificador"},
            "Cerrada eficaz": {"responsable"},
            "Cerrada no eficaz": {"responsable"},
        }
        for estado, esperados in casos.items():
            with self.subTest(estado=estado):
                self.assertEqual(self._nuestros(R_NC, self._nc(estado)), self._p(*esperados))

    def test_no_conformidad_sin_verificador_avisa_a_dpgc(self):
        self.assertIn(self.persona["dpgc"], self._para(R_NC, self._nc("En verificacion", verificada_por=None)))

    def test_no_conformidad_sin_responsable_avisa_al_rol_de_calidad(self):
        para = self._para(R_NC, self._nc("En tratamiento", responsable=None))
        self.assertIn(self.persona["calidad-programa"], para)

    def test_accion_de_mejora_avisa_a_quien_actua_en_cada_estado(self):
        casos = {
            "En ejecucion": {"responsable"},
            "Ejecutada": {"verificador"},
            "Verificada eficaz": {"responsable"},
            "Verificada no eficaz": {"responsable"},
        }
        for estado, esperados in casos.items():
            with self.subTest(estado=estado):
                doc = frappe.get_doc(
                    {
                        "doctype": "Accion Mejora",
                        "name": "AM-PRUEBA-TRANSICION",
                        "codigo": "AM-PRUEBA-TRANSICION",
                        "estado": estado,
                        "responsable": self.persona["responsable"],
                        "verificada_por": self.persona["verificador"],
                    }
                )
                self.assertEqual(self._nuestros(R_ACCION, doc), self._p(*esperados))

    # --- Auditoría y hallazgo ------------------------------------------------

    def _auditoria(self, estado, equipo=True):
        doc = frappe.get_doc(
            {"doctype": "Auditoria", "name": "AUD-PRUEBA-TRANSICION", "titulo": "Auditoría de prueba", "estado": estado}
        )
        if equipo:
            doc.append("equipo", {"usuario": self.persona["auditor-equipo"], "rol": "Auditor lider"})
        return doc

    def test_auditoria_avisa_al_equipo_y_el_informe_a_dpgc(self):
        for estado in ("En ejecucion", "Ejecutada", "Cerrada"):
            with self.subTest(estado=estado):
                self.assertEqual(self._nuestros(R_AUDITORIA, self._auditoria(estado)), self._p("auditor-equipo"))

        informe = self._nuestros(R_AUDITORIA, self._auditoria("Informe emitido"))
        self.assertEqual(informe, self._p("dpgc"))

    def test_auditoria_sin_equipo_avisa_a_los_auditores(self):
        self.assertIn(self.persona["auditor"], self._para(R_AUDITORIA, self._auditoria("En ejecucion", equipo=False)))

    def test_hallazgo_escalado_avisa_a_dpgc(self):
        doc = frappe.get_doc(
            {"doctype": "Hallazgo Auditoria", "name": "HA-PRUEBA", "codigo": "HA-PRUEBA", "estado": "Escalado a NC"}
        )
        self.assertEqual(self._nuestros(R_HALLAZGO, doc), self._p("dpgc"))

    # --- el envío de verdad, con una No Conformidad --------------------------

    def _nc_real(self):
        factories.desactivar_workflow("No Conformidad")
        doc = frappe.get_doc(
            {"doctype": "No Conformidad", "titulo": "NC de prueba", "responsable": self.persona["responsable"]}
        ).insert(ignore_permissions=True)
        self.sendmail.reset_mock()
        return doc.name

    def _pasar_a(self, nombre, estado):
        # Documento recién leído: Frappe no reevalúa una regla ya ejecutada sobre
        # la MISMA instancia (`flags.notifications_executed`).
        doc = frappe.get_doc("No Conformidad", nombre)
        doc.estado = estado
        doc.save(ignore_permissions=True)

    def test_una_transicion_real_envia_un_correo_al_responsable(self):
        nombre = self._nc_real()

        self._pasar_a(nombre, "En analisis")

        self.assertEqual(self.sendmail.call_count, 1)
        self.assertEqual(self.sendmail.call_args.kwargs["recipients"], [self.persona["responsable"]])
        self.assertIn("En analisis", self.sendmail.call_args.kwargs["subject"])

    def test_guardar_sin_cambiar_el_estado_no_envia(self):
        nombre = self._nc_real()
        self._pasar_a(nombre, "En analisis")
        self.sendmail.reset_mock()

        doc = frappe.get_doc("No Conformidad", nombre)
        doc.descripcion = "Otra redacción, mismo estado"
        doc.save(ignore_permissions=True)

        self.sendmail.assert_not_called()

    def test_en_ensayo_la_transicion_no_envia_y_queda_registrada(self):
        frappe.db.set_single_value("Configuracion Correo", "modo", correo.ENSAYO)
        nombre = self._nc_real()

        self._pasar_a(nombre, "En analisis")

        self.sendmail.assert_not_called()
        self.assertTrue(
            frappe.db.exists(
                "Registro Correo",
                {"regla": R_NC, "documento": nombre, "destinatario": self.persona["responsable"]},
            )
        )

    def test_si_el_correo_falla_el_documento_se_guarda_igual(self):
        nombre = self._nc_real()
        self.sendmail.side_effect = Exception("SMTP caído")

        self._pasar_a(nombre, "En analisis")

        self.assertEqual(frappe.db.get_value("No Conformidad", nombre, "estado"), "En analisis")

    # --- vencimientos (f7) ---------------------------------------------------

    def test_un_vencimiento_avisa_un_solo_dia(self):
        """`Days Before` elige los documentos cuya fecha cae justo a N días: uno por día."""
        f7.run()
        frappe.flags.in_patch = False
        regla = frappe.get_doc("Notification", "SGC - Accion de mejora por vencer")
        dias = regla.days_in_advance

        justo = frappe.get_doc(
            {"doctype": "Accion Mejora", "fecha_compromiso": add_days(nowdate(), dias)}
        ).insert(ignore_permissions=True)
        un_dia_antes = frappe.get_doc(
            {"doctype": "Accion Mejora", "fecha_compromiso": add_days(nowdate(), dias + 1)}
        ).insert(ignore_permissions=True)

        hoy = {d.name for d in regla.get_documents_for_today()}
        self.assertIn(justo.name, hoy)
        self.assertNotIn(un_dia_antes.name, hoy)

    # --- la actualización ----------------------------------------------------

    def test_el_parche_pasa_a_correo_las_reglas_de_campana(self):
        prueba = "SGC - Prueba canal heredado"
        frappe.get_doc(
            {
                "doctype": "Notification",
                "name": prueba,
                "subject": "Prueba",
                "document_type": "ToDo",
                "event": "New",
                "channel": "System Notification",
                "message": "Prueba",
                "enabled": 0,
                "recipients": [{"receiver_by_role": "DPGC"}],
            }
        ).insert(ignore_permissions=True)
        ajena = "Prueba canal ajeno al SGC"
        frappe.get_doc(
            {
                "doctype": "Notification",
                "name": ajena,
                "subject": "Prueba",
                "document_type": "ToDo",
                "event": "New",
                "channel": "System Notification",
                "message": "Prueba",
                "enabled": 0,
                "recipients": [{"receiver_by_role": "DPGC"}],
            }
        ).insert(ignore_permissions=True)

        notificaciones_por_correo.execute()

        self.assertEqual(frappe.db.get_value("Notification", prueba, "channel"), "Email")
        self.assertEqual(frappe.db.get_value("Notification", prueba, "send_system_notification"), 1)
        # Solo toca las del SGC: una regla de otra app o creada a mano no es suya.
        self.assertEqual(frappe.db.get_value("Notification", ajena, "channel"), "System Notification")
