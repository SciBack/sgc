# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Latido del scheduler (#42) contra una instancia real.

Dos cosas distintas, en dos clases:

1. **La marca.** No la sellamos nosotros: la sella Frappe en `Scheduled Job Log`.
   Aquí se fija que la marca de la que depende la vigilancia significa lo que
   creemos —`Complete` solo si la tarea terminó bien—, corriendo una tarea del
   app por el mismo camino que la corre el scheduler. Si una versión de Frappe
   cambiara eso, la vigilancia mentiría, y estos tests son los que avisarían.
   `ScheduledJobType.execute` hace commit, así que se limpian sus logs a mano.

2. **El aviso.** Se monta el estado en la base —marcas antiguas o recientes— y
   se comprueba lo que decide `sgc.latido` y lo que ve `sgc.verificacion`. Todo
   sin commit y deshecho al final de cada test.
"""
from unittest.mock import patch

import frappe
from frappe.core.doctype.scheduled_job_type.scheduled_job_type import sync_jobs
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

from sgc import latido
from sgc.verificacion import AVISO, verificar

METODO = "sgc.tasks.marcar_acuerdos_vencidos"


def _tipos_del_app():
    if not frappe.db.exists("Scheduled Job Type", {"method": ["like", "sgc.%"]}):
        sync_jobs()
    return frappe.get_all("Scheduled Job Type", filters={"method": ["like", "sgc.%"]}, pluck="name", limit=0)


class IntegrationTestMarcaNativa(IntegrationTestCase):
    def setUp(self):
        _tipos_del_app()
        self.tipo = frappe.get_doc("Scheduled Job Type", {"method": METODO})
        self.previos = set(
            frappe.get_all("Scheduled Job Log", filters={"scheduled_job_type": self.tipo.name}, pluck="name", limit=0)
        )

    def tearDown(self):
        for nombre in self._nuevos():
            frappe.delete_doc("Scheduled Job Log", nombre, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _nuevos(self):
        actuales = frappe.get_all(
            "Scheduled Job Log", filters={"scheduled_job_type": self.tipo.name}, pluck="name", limit=0
        )
        return [n for n in actuales if n not in self.previos]

    def _estados_nuevos(self):
        return [frappe.db.get_value("Scheduled Job Log", n, "status") for n in self._nuevos()]

    def test_una_tarea_que_termina_bien_deja_marca_complete(self):
        self.tipo.execute()
        self.assertEqual(self._estados_nuevos(), ["Complete"])

    def test_una_tarea_que_lanza_no_deja_marca_complete(self):
        """Si un fallo sellara la marca, un fallo repetido parecería salud."""
        with patch(METODO, side_effect=RuntimeError("fallo simulado")):
            self.tipo.execute()
        self.assertEqual(self._estados_nuevos(), ["Failed"])


class IntegrationTestAvisoLatido(IntegrationTestCase):
    def setUp(self):
        self.tipos = _tipos_del_app()
        frappe.db.commit()
        # Estado propio: se borran las marcas del app (sin commit) y se siembran
        # las del escenario. El scheduler «encendido» se fuerza porque en el CI
        # y en el lab suele estar desactivado, y eso ya daría aviso por sí solo.
        frappe.db.delete("Scheduled Job Log", {"scheduled_job_type": ["in", self.tipos]})
        for tipo in self.tipos:
            frappe.db.set_value(
                "Scheduled Job Type", tipo, "creation", add_to_date(now_datetime(), days=-30), update_modified=False
            )
        self.encendido = patch.object(latido, "_scheduler_apagado", return_value=False)
        self.encendido.start()

    def tearDown(self):
        self.encendido.stop()
        frappe.db.rollback()

    def _sembrar(self, horas):
        for tipo in self.tipos:
            log = frappe.get_doc(doctype="Scheduled Job Log", scheduled_job_type=tipo, status="Complete").insert(
                ignore_permissions=True
            )
            frappe.db.set_value(
                "Scheduled Job Log",
                log.name,
                "modified",
                add_to_date(now_datetime(), hours=-horas),
                update_modified=False,
            )

    def test_una_marca_de_hace_tres_dias_avisa(self):
        self._sembrar(horas=72)

        resultado = latido.comprobar()

        self.assertTrue(resultado["alerta"])
        self.assertTrue(all(f["atrasada"] for f in resultado["tareas"]))
        hallazgo = next((h for h in verificar() if h.codigo == "scheduler-parado"), None)
        self.assertIsNotNone(hallazgo)
        self.assertEqual(hallazgo.nivel, AVISO)
        self.assertTrue(any(METODO in linea for linea in hallazgo.detalle))

    def test_con_el_scheduler_corriendo_no_hay_aviso(self):
        self._sembrar(horas=6)

        self.assertFalse(latido.comprobar()["alerta"])
        self.assertNotIn("scheduler-parado", [h.codigo for h in verificar()])

    def test_el_umbral_sale_de_site_config(self):
        self._sembrar(horas=72)

        with patch.dict(frappe.local.conf, {latido.CLAVE_UMBRAL: 96}):
            self.assertEqual(latido.umbral_horas(), 96)
            self.assertFalse(latido.comprobar()["alerta"])

    def test_solo_un_system_manager_puede_consultarlo(self):
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                latido.estado()
        finally:
            frappe.set_user("Administrator")
