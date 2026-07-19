# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Tests de integración del job programado `sgc.tasks.marcar_evidencias_vencidas`.

Cubre el gap real que el job cierra: `Evidencia.on_update` solo marca "Vencida"
cuando alguien guarda el documento (ver
sgc/sgc_nucleo/doctype/evidencia/evidencia.py::_marcar_vencida_si_expiro); si
nadie lo vuelve a tocar tras la fecha de vencimiento, se queda "Pendiente"/
"Valida" para siempre. Estos tests siembran esa situación con un
`frappe.db.set_value` directo (no `doc.save()`, para no disparar el propio
auto-flip del controlador) y verifican que el job, corrido de forma aislada,
la corrige.

`marcar_evidencias_vencidas()` hace `frappe.db.commit()` al final (correcto:
un scheduled job real corre fuera de una transacción de request y DEBE
comitear) -- pero eso rompe el rollback automático entre tests de
`IntegrationTestCase` para el propio test que la invoca, y dos invocaciones
separadas de `bench run-tests` reutilizan el mismo código determinista de
`factories.crear_evidencia` (secuencia `_seq` reiniciada por proceso). Sin
resetear el estado explícitamente, la 2da corrida encuentra la MISMA
Evidencia ya "Vencida" (residuo comiteado de la 1ra corrida) en vez de una
"Pendiente" fresca. Por eso cada test resetea estado/vigencia con
`frappe.db.set_value` antes de sembrar su propio escenario.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc.tasks import marcar_evidencias_vencidas
from sgc.tests import factories


class IntegrationTestTasks(IntegrationTestCase):
    """Integration tests para el scheduled job de vencimiento de Evidencia."""

    def _nueva_evidencia_pendiente(self, **kw):
        """Evidencia Pendiente vía insert() normal (arranca en el estado inicial
        del workflow `Evidencia SGC` -- eso sí está permitido).
        """
        vals = {
            "titulo": "Evidencia de prueba (job vencimiento)",
            "tipo": "Enlace",
            "enlace_url": "https://example.test/evidencia-job",
        }
        vals.update(kw)
        return factories.crear_evidencia(**vals)

    def test_marca_vencida_evidencia_pendiente_expirada(self):
        """Pendiente + vigencia_hasta pasada, sin guardar tras expirar -> el job la marca Vencida."""
        ev = self._nueva_evidencia_pendiente()
        # Resetea explícito: `ev` puede ser residuo ya "Vencida" de una corrida
        # anterior de la suite (ver docstring de módulo).
        frappe.db.set_value("Evidencia", ev.name, "estado", "Pendiente", update_modified=False)
        ayer = add_days(nowdate(), -1)
        # set_value directo: no pasa por controller/validate, simula el "nadie la tocó".
        frappe.db.set_value("Evidencia", ev.name, "vigencia_hasta", ayer, update_modified=False)
        self.assertEqual(frappe.db.get_value("Evidencia", ev.name, "estado"), "Pendiente")

        marcar_evidencias_vencidas()

        self.assertEqual(frappe.db.get_value("Evidencia", ev.name, "estado"), "Vencida")

    def test_marca_vencida_evidencia_valida_expirada(self):
        """Valida + vigencia_hasta pasada -> el job también la marca Vencida."""
        arbol = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo="TEST-TASKS")
        criterio = arbol["criterios"][arbol["estandares"][0]][0]

        ev = self._nueva_evidencia_pendiente()
        # Resetea explícito por el mismo motivo que arriba -- incluida
        # `vigencia_hasta`: si quedó en el pasado por residuo, el propio
        # `on_update` de Evidencia la marcaría Vencida en el `.save()` de abajo
        # ANTES de que el test llegue a fijar su propia fecha vencida.
        frappe.db.set_value("Evidencia", ev.name,
            {"estado": "Pendiente", "vigencia_hasta": None}, update_modified=False)
        # Idempotente: si `ev` es residuo de una corrida anterior, la Trazabilidad
        # ya puede existir -- crearla de nuevo chocaría con el "vínculo duplicado".
        if not frappe.db.exists("Trazabilidad", {"evidencia": ev.name, "elemento_marco": criterio}):
            factories.crear_trazabilidad(ev, elemento_marco=criterio)
        ev.reload()
        ev.estado = "Valida"
        ev.save(ignore_permissions=True)
        self.assertEqual(frappe.db.get_value("Evidencia", ev.name, "estado"), "Valida")

        ayer = add_days(nowdate(), -1)
        frappe.db.set_value("Evidencia", ev.name, "vigencia_hasta", ayer, update_modified=False)

        marcar_evidencias_vencidas()

        self.assertEqual(frappe.db.get_value("Evidencia", ev.name, "estado"), "Vencida")

    def test_no_toca_evidencia_con_vigencia_futura(self):
        """vigencia_hasta en el futuro -> el job no la toca, sigue Pendiente."""
        ev = self._nueva_evidencia_pendiente()
        frappe.db.set_value("Evidencia", ev.name, "estado", "Pendiente", update_modified=False)
        maniana = add_days(nowdate(), 30)
        frappe.db.set_value("Evidencia", ev.name, "vigencia_hasta", maniana, update_modified=False)

        marcar_evidencias_vencidas()

        self.assertEqual(frappe.db.get_value("Evidencia", ev.name, "estado"), "Pendiente")

    def test_no_toca_evidencia_en_otro_estado_de_gestion(self):
        """Observada + vigencia pasada -> el job la deja intacta (solo actúa sobre
        Pendiente/Valida, mismo alcance que `_marcar_vencida_si_expiro`).
        """
        ev = self._nueva_evidencia_pendiente()
        ev.estado = "Observada"
        ev.save(ignore_permissions=True)

        ayer = add_days(nowdate(), -1)
        frappe.db.set_value("Evidencia", ev.name, "vigencia_hasta", ayer, update_modified=False)

        marcar_evidencias_vencidas()

        self.assertEqual(frappe.db.get_value("Evidencia", ev.name, "estado"), "Observada")

    def test_sin_evidencias_vencidas_no_falla(self):
        """Sin ninguna Evidencia vencida en BD, el job corre sin error (no-op)."""
        marcar_evidencias_vencidas()
