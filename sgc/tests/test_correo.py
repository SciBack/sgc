# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Correo (#41) contra una instancia real: la regla, el rol y el envío de verdad.

Se monta una `Notification` de canal Email con destinatarios por rol y en copia,
y se la hace enviar con `Notification.send`, el mismo camino que usa el
scheduler. Lo que se comprueba es lo que queda en la cola de Frappe (`Email
Queue`): a quién va y en qué estado, que es lo que decide el SGC en su gancho
`before_insert`. Que el correo salga luego por SMTP es cosa de Frappe y de la
cuenta de correo, no de esta prueba.

Todo se deshace al final de cada test (sin commit).
"""
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
        frappe.get_doc("Notification", REGLA).send(self.todo)

    def _cola(self, referencia=None):
        """[(estado, [destinatarios])] de lo que la regla dejó en la cola."""
        colas = frappe.get_all(
            "Email Queue",
            filters={"reference_doctype": "ToDo", "reference_name": referencia or self.todo.name},
            fields=["name", "status"],
            order_by="creation",
        )
        return [
            (
                c.status,
                sorted(
                    frappe.get_all("Email Queue Recipient", filters={"parent": c.name}, pluck="recipient")
                ),
            )
            for c in colas
        ]

    def _registros(self):
        return frappe.get_all(
            "Registro Correo",
            filters={"documento": self.todo.name, "aviso": ["is", "not set"]},
            fields=["destinatario", "tipo", "resultado", "asunto"],
            order_by="destinatario",
        )

    # --- la intercepción ---------------------------------------------------

    def test_el_filtro_es_un_gancho_estandar_de_la_cola(self):
        """Nada de sobrescribir clases de Frappe: un `doc_events` sobre `Email Queue`."""
        self.assertIn("sgc.correo.filtrar_cola", frappe.get_hooks("doc_events")["Email Queue"]["before_insert"])
        self.assertNotIn("Notification", frappe.get_hooks("override_doctype_class"))
        self.assertNotIn("Notification Log", frappe.get_hooks("override_doctype_class"))

    def test_en_ensayo_no_se_envia_y_queda_registrado(self):
        self._configurar("Ensayo")

        self._enviar()

        self.assertEqual(self._cola(), [("Error", [])])
        registros = self._registros()
        self.assertEqual([r.destinatario for r in registros], [EN_COPIA, USUARIO])
        self.assertEqual({r.resultado for r in registros}, {correo.NO_ENVIADO})
        self.assertEqual({r.tipo for r in registros}, {"CC", "Para"})
        self.assertEqual(registros[0].asunto, f"Prueba {self.todo.name}")

    def test_el_ensayo_no_apaga_la_campana_del_desk(self):
        """El ensayo es del correo. Los avisos internos siguen llegando."""
        self._configurar("Ensayo")
        frappe.db.set_value("Notification", REGLA, "send_system_notification", 1)

        self._enviar()

        self.assertEqual(self._cola(), [("Error", [])])
        self.assertTrue(
            frappe.db.exists(
                "Notification Log",
                {"for_user": USUARIO, "document_type": "ToDo", "document_name": self.todo.name},
            )
        )

    def test_con_lista_blanca_solo_se_envia_a_quien_esta_en_ella(self):
        self._configurar("Real", USUARIO)

        self._enviar()

        self.assertEqual(self._cola(), [("Not Sent", [USUARIO])])
        registros = self._registros()
        self.assertEqual([(r.destinatario, r.resultado) for r in registros], [(EN_COPIA, correo.OMITIDO)])

    def test_en_real_sin_lista_blanca_se_envia_a_todos(self):
        self._configurar("Real")

        self._enviar()

        self.assertEqual(self._cola(), [("Not Sent", sorted([USUARIO, EN_COPIA]))])
        self.assertEqual(self._registros(), [])

    def test_el_asunto_codificado_se_lee_legible(self):
        crudo = "Subject: =?utf-8?q?Revisi=C3=B3n_pendiente?=\n\ncuerpo"
        self.assertEqual(correo.asunto_del_mensaje(crudo), "Revisión pendiente")

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

    # --- el correo de la campana (#35) ----------------------------------------
    # Frappe lo encola sin referencia al documento (notification_log.py, send_notification_email):
    # se captura lo que entra en la cola y en el registro mientras se crea el aviso.

    def _aviso_desk(self, tipo="Assignment"):
        colas_antes = set(frappe.get_all("Email Queue", pluck="name"))
        registros_antes = set(frappe.get_all("Registro Correo", pluck="name"))
        aviso = frappe.get_doc(
            {
                "doctype": "Notification Log",
                "for_user": USUARIO,
                "from_user": "Administrator",
                "type": tipo,
                "subject": "Administrator te asignó una <b>tarea</b>",
                "document_type": "ToDo",
                "document_name": self.todo.name,
            }
        ).insert(ignore_permissions=True)
        colas = [
            (
                frappe.db.get_value("Email Queue", c, "status"),
                sorted(frappe.get_all("Email Queue Recipient", filters={"parent": c}, pluck="recipient")),
            )
            for c in frappe.get_all("Email Queue", pluck="name")
            if c not in colas_antes
        ]
        registros = [
            (r.destinatario, r.resultado)
            for r in frappe.get_all("Registro Correo", fields=["name", "destinatario", "resultado"])
            if r.name not in registros_antes
        ]
        return aviso, colas, registros

    def test_en_ensayo_el_aviso_del_desk_no_manda_correo_y_queda_registrado(self):
        self._configurar("Ensayo")

        aviso, colas, registros = self._aviso_desk()

        self.assertTrue(frappe.db.exists("Notification Log", aviso.name), "la campana se crea igual")
        self.assertEqual(colas, [("Error", [])])
        self.assertEqual(registros, [(USUARIO, correo.NO_ENVIADO)])

    def test_fuera_de_la_lista_blanca_el_aviso_del_desk_se_omite(self):
        self._configurar("Real", "otra-persona@example.com")

        _, colas, registros = self._aviso_desk()

        self.assertEqual(colas, [("Error", [])])
        self.assertEqual(registros, [(USUARIO, correo.OMITIDO)])

    def test_en_la_lista_blanca_el_aviso_del_desk_sale(self):
        self._configurar("Real", USUARIO)

        _, colas, registros = self._aviso_desk()

        self.assertEqual([para for _estado, para in colas], [[USUARIO]])
        self.assertEqual(registros, [])

    def test_un_aviso_que_no_manda_correo_no_se_registra(self):
        """`Alert` es la campana de las reglas: Frappe nunca le añade correo, así
        que no hay nada retenido que anotar."""
        self._configurar("Ensayo")

        _, colas, registros = self._aviso_desk(tipo="Alert")

        self.assertEqual(colas, [])
        self.assertEqual(registros, [])
