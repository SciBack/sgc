# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Correo (#41) contra una instancia real: la regla, el rol y el envío de verdad.

Se monta una `Notification` de canal Email con destinatarios por rol y en copia,
y se la hace enviar con `Notification.send`, el mismo camino que usa el
scheduler. `frappe.sendmail` se sustituye por un mock: lo que se comprueba es a
quién se le PIDE enviar, que es lo que decide el SGC. Que el correo salga luego
por SMTP es cosa de Frappe y de la cuenta de correo, no de esta prueba —y así no
depende de que el CI tenga una configurada—.

Todo se deshace al final de cada test (sin commit).
"""
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sgc import correo
from sgc.patches import correo_conservar_envio_real
from sgc.verificacion import AVISO, verificar

ROL = "SGC Prueba Correo"
ROL_VACIO = "SGC Prueba Correo Vacio"
USUARIO = "sgc-prueba-correo@example.com"
EN_COPIA = "copia-prueba-correo@example.com"
REGLA = "SGC Prueba - Correo"


class IntegrationTestCorreo(IntegrationTestCase):
    def setUp(self):
        for rol in (ROL, ROL_VACIO):
            if not frappe.db.exists("Role", rol):
                frappe.get_doc({"doctype": "Role", "role_name": rol, "desk_access": 1}).insert(
                    ignore_permissions=True
                )
        if not frappe.db.exists("User", USUARIO):
            usuario = frappe.get_doc(
                {"doctype": "User", "email": USUARIO, "first_name": "Prueba Correo", "send_welcome_email": 0}
            )
            usuario.append("roles", {"role": ROL})
            usuario.insert(ignore_permissions=True)

        if frappe.db.exists("Notification", REGLA):
            frappe.delete_doc("Notification", REGLA, force=True, ignore_permissions=True)
        # enabled=0: la regla no debe dispararse sola con los ToDo del test; se
        # envía a mano con `send()`, que no mira `enabled`.
        frappe.get_doc(
            {
                "doctype": "Notification",
                "name": REGLA,
                "subject": "Prueba {{ doc.name }}",
                "document_type": "ToDo",
                "event": "New",
                "channel": "Email",
                "message": "Mensaje de prueba",
                "enabled": 0,
                "recipients": [{"receiver_by_role": ROL, "cc": EN_COPIA}],
            }
        ).insert(ignore_permissions=True)
        self.todo = frappe.get_doc({"doctype": "ToDo", "description": "Prueba de correo"}).insert(
            ignore_permissions=True
        )

    def tearDown(self):
        frappe.db.rollback()

    def _configurar(self, modo, lista=""):
        frappe.db.set_single_value("Configuracion Correo", {"modo": modo, "lista_blanca": lista})

    def _enviar(self):
        regla = frappe.get_doc("Notification", REGLA)
        with patch("frappe.sendmail") as sendmail:
            regla.send(self.todo)
        return sendmail

    def _registros(self):
        return frappe.get_all(
            "Registro Correo",
            filters={"regla": REGLA, "documento": self.todo.name},
            fields=["destinatario", "tipo", "resultado", "asunto"],
            order_by="destinatario",
        )

    # --- la intercepción ---------------------------------------------------

    def test_la_regla_usa_la_clase_del_sgc(self):
        self.assertIsInstance(frappe.get_doc("Notification", REGLA), correo.NotificacionSGC)

    def test_en_ensayo_no_se_envia_y_queda_registrado(self):
        self._configurar("Ensayo")

        sendmail = self._enviar()

        sendmail.assert_not_called()
        registros = self._registros()
        self.assertEqual([r.destinatario for r in registros], [EN_COPIA, USUARIO])
        self.assertEqual({r.resultado for r in registros}, {correo.NO_ENVIADO})
        self.assertEqual({r.tipo for r in registros}, {"CC", "Para"})
        self.assertEqual(registros[0].asunto, f"Prueba {self.todo.name}")

    def test_con_lista_blanca_solo_se_envia_a_quien_esta_en_ella(self):
        self._configurar("Real", USUARIO)

        sendmail = self._enviar()

        sendmail.assert_called_once()
        self.assertEqual(sendmail.call_args.kwargs["recipients"], [USUARIO])
        self.assertEqual(sendmail.call_args.kwargs["cc"], [])
        registros = self._registros()
        self.assertEqual([(r.destinatario, r.resultado) for r in registros], [(EN_COPIA, correo.OMITIDO)])

    def test_en_real_sin_lista_blanca_se_envia_a_todos(self):
        self._configurar("Real")

        sendmail = self._enviar()

        sendmail.assert_called_once()
        self.assertEqual(sendmail.call_args.kwargs["recipients"], [USUARIO])
        self.assertEqual(sendmail.call_args.kwargs["cc"], [EN_COPIA])
        self.assertEqual(self._registros(), [])

    # --- la comprobación previa --------------------------------------------

    def test_la_comprobacion_senala_el_rol_vacio_y_no_el_poblado(self):
        frappe.db.set_value("Notification", REGLA, "enabled", 1)
        frappe.get_doc("Notification", REGLA).append("recipients", {"receiver_by_role": ROL_VACIO}).db_insert()

        vacios = correo.roles_sin_destinatarios()

        self.assertIn((REGLA, ROL_VACIO), vacios)
        self.assertNotIn((REGLA, ROL), vacios)
        regla = next(r for r in correo.comprobar_destinatarios() if r["regla"] == REGLA)
        poblado = next(d for d in regla["destinos"] if d.get("valor") == ROL)
        self.assertEqual(poblado["correos"], [USUARIO])

        hallazgo = next((h for h in verificar() if h.codigo == "correo-rol-sin-destinatarios"), None)
        self.assertIsNotNone(hallazgo)
        self.assertEqual(hallazgo.nivel, AVISO)
        self.assertTrue(any(REGLA in linea and ROL_VACIO in linea for linea in hallazgo.detalle))

    # --- la configuración ----------------------------------------------------

    def test_pasar_a_real_y_vaciar_la_lista_son_dos_actos(self):
        conf = frappe.get_single("Configuracion Correo")
        conf.modo = "Ensayo"
        conf.lista_blanca = USUARIO
        conf.save(ignore_permissions=True)

        conf.modo = "Real"
        conf.lista_blanca = ""
        with self.assertRaises(frappe.ValidationError):
            conf.save(ignore_permissions=True)

        conf.reload()
        conf.modo = "Real"
        conf.save(ignore_permissions=True)
        conf.lista_blanca = ""
        conf.save(ignore_permissions=True)
        self.assertEqual(correo.modo(), "Real")
        self.assertEqual(correo.lista_blanca(), [])

    def test_la_lista_blanca_rechaza_lo_que_no_es_un_correo(self):
        conf = frappe.get_single("Configuracion Correo")
        conf.lista_blanca = f"{USUARIO}\nesto-no-es-un-correo"
        with self.assertRaises(frappe.ValidationError):
            conf.save(ignore_permissions=True)

    def test_solo_un_system_manager_ve_el_estado(self):
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                correo.estado()
        finally:
            frappe.set_user("Administrator")

    # --- la actualización ----------------------------------------------------

    def test_un_sitio_que_ya_enviaba_conserva_el_envio_real(self):
        frappe.db.set_value("Notification", REGLA, "enabled", 1)
        frappe.db.set_single_value("Configuracion Correo", "modo", None)

        correo_conservar_envio_real.execute()

        self.assertEqual(correo.modo(), "Real")

    def test_un_sitio_sin_correo_queda_en_ensayo(self):
        for nombre in frappe.get_all("Notification", filters={"channel": "Email", "enabled": 1}, pluck="name"):
            frappe.db.set_value("Notification", nombre, "enabled", 0)
        frappe.db.set_single_value("Configuracion Correo", "modo", None)

        correo_conservar_envio_real.execute()

        self.assertEqual(correo.modo(), "Ensayo")

    def test_el_parche_no_pisa_una_decision_tomada(self):
        frappe.db.set_value("Notification", REGLA, "enabled", 1)
        frappe.db.set_single_value("Configuracion Correo", "modo", "Ensayo")

        correo_conservar_envio_real.execute()

        self.assertEqual(correo.modo(), "Ensayo")
