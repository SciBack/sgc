# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""¿Se avisó de la ventana de mantenimiento? (#55)

Los comunicados se fechan en 2099 y se consulta con un `momento` fijo: los tests no dependen del
reloj ni de los comunicados que ya tenga el sitio. Se marcan como enviados con `set_value`, sin
pasar por el envío, que ya prueba test_funciones_correo.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, get_datetime

from sgc import mantenimiento

INICIO = get_datetime("2099-06-01 22:00:00")
FIN = get_datetime("2099-06-01 23:30:00")


class IntegrationTestVentanaAvisada(IntegrationTestCase):
    def setUp(self):
        frappe.db.savepoint("ventana_avisada")

    def tearDown(self):
        frappe.db.rollback(save_point="ventana_avisada")

    def _comunicado(self, estado="Enviado", tipo="Mantenimiento programado", inicio=INICIO, fin=FIN):
        c = frappe.get_doc({
            "doctype": "Comunicado",
            "asunto": "Actualización del sistema",
            "tipo": tipo,
            "mensaje": "<p>El sistema se actualiza.</p>",
            "roles": [{"rol": "System Manager"}],
            "inicio_mantenimiento": inicio,
            "fin_mantenimiento": fin,
        }).insert(ignore_permissions=True)
        if estado == "Enviado":
            frappe.db.set_value("Comunicado", c.name, {"estado": "Enviado", "n_destinatarios": 7})
        return c

    def _a(self, minutos):
        return mantenimiento.ventana_avisada(add_to_date(INICIO, minutes=minutos))

    def test_sin_comunicado_no_hay_aviso(self):
        self.assertEqual(self._a(10)["avisado"], False)

    def test_dentro_de_la_ventana_esta_avisado(self):
        c = self._comunicado()
        resultado = self._a(45)
        self.assertTrue(resultado["avisado"])
        self.assertEqual(resultado["comunicado"], c.name)
        self.assertEqual(resultado["destinatarios"], 7)

    def test_se_puede_empezar_un_poco_antes_pero_no_mucho(self):
        self._comunicado()
        self.assertTrue(self._a(-20)["avisado"])
        self.assertFalse(self._a(-45)["avisado"])

    def test_despues_del_fin_ya_no_cubre(self):
        self._comunicado()
        self.assertFalse(self._a(100)["avisado"])

    def test_sin_fin_solo_cubre_el_arranque(self):
        self._comunicado(fin=None)
        self.assertTrue(self._a(10)["avisado"])
        self.assertFalse(self._a(120)["avisado"])

    def test_un_borrador_no_es_un_aviso(self):
        self._comunicado(estado="Borrador")
        self.assertFalse(self._a(10)["avisado"])

    def test_otro_tipo_de_comunicado_no_es_un_aviso(self):
        self._comunicado(tipo="Aviso general")
        self.assertFalse(self._a(10)["avisado"])
