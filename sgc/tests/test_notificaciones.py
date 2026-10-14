# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Los avisos del SGC (M17, #29) como Notification estándar de Frappe.

Desde la 1.2.0 cada aviso es un fichero en la carpeta de su módulo (`sgc/<módulo>/notification/`)
que Frappe sincroniza en cada `migrate`. Hasta entonces los creaban f7 y f15 en cada migrate.
Lo que se prueba es lo que esos ficheros tienen que cumplir y que llegan a la base.
"""

import frappe
from frappe.tests import IntegrationTestCase

from sgc import estandar

# Los avisos de vencimiento y convocatoria (antes f7), por DocType.
VENCIMIENTOS = {"Documento Controlado", "Evidencia", "Accion Mejora", "Plan Mejora", "Reunion", "Ficha Indicador"}


class IntegrationTestNotificaciones(IntegrationTestCase):
    def test_cada_aviso_estandar_esta_en_la_base(self):
        avisos = estandar.avisos()
        self.assertGreaterEqual(len(avisos), 20)
        for nombre in avisos:
            with self.subTest(aviso=nombre):
                self.assertEqual(frappe.db.get_value("Notification", nombre, "is_standard"), 1)

    def test_son_de_correo_con_campana_y_declaran_modulo(self):
        """#29: correo y campana; qué sale de verdad lo decide Configuracion Correo (#41)."""
        for nombre, aviso in estandar.avisos().items():
            with self.subTest(aviso=nombre):
                self.assertEqual(aviso["channel"], "Email")
                self.assertEqual(aviso.get("send_system_notification"), 1)
                self.assertTrue(aviso.get("module", "").startswith("SGC "))

    def test_los_de_fecha_vigilan_un_campo_de_fecha(self):
        for nombre, aviso in estandar.avisos().items():
            if aviso["event"] in ("Days Before", "Days After"):
                with self.subTest(aviso=nombre):
                    self.assertTrue(aviso.get("date_changed"))

    def test_cubre_los_vencimientos_y_la_convocatoria(self):
        con_fecha = {a["document_type"] for a in estandar.avisos().values() if a["event"] in ("Days Before", "Days After", "New")}
        self.assertTrue(VENCIMIENTOS <= con_fecha, VENCIMIENTOS - con_fecha)

    def test_ninguno_nombra_a_una_institucion(self):
        """El canónico vale para cualquier universidad (#65)."""
        import json

        texto = json.dumps(estandar.avisos(), ensure_ascii=False).lower()
        for marca in ("upeu", "universidad peruana", "juliaca", "tarapoto"):
            self.assertNotIn(marca, texto)
