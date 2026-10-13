# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Migas de pan coherentes en el Desk (revisión del 27-sep-2026).

Desde la 1.1.0 el Desk del SGC son ficheros estándar de Frappe (ver `sgc/escritorio.py`):
la miga y el menú los resuelve Frappe solo, sin código propio en el navegador. Lo que se
prueba aquí es lo que esos ficheros tienen que cumplir:

  - cada pantalla, área e informe tiene nombre humano en `translations/es.csv`
    (sin él, la miga pinta el nombre técnico sin tilde: «Accion Mejora»);
  - cada área tiene su portada (Workspace estándar) y su menú (Sidebar estándar),
    sincronizados en la base;
  - ninguna pantalla está en dos menús;
  - no queda código que parchee el Desk de Frappe.
"""

import csv
import os

import frappe
from frappe.tests import IntegrationTestCase

from sgc import escritorio

APP = "sgc"

# Pantallas cuyo nombre técnico ya es el nombre correcto en español: no llevan
# traducción. Una pantalla nueva va al CSV o aquí, a conciencia.
IGUALES_EN_ESPANOL = {
    "Acuerdo", "Comunicado", "Evidencia", "Hallazgo", "Indicador", "Instrumento",
    "Procedimiento", "Proceso", "Programa", "Riesgo", "Trazabilidad",
}


def _traducciones():
    ruta = os.path.join(frappe.get_app_path(APP), "translations", "es.csv")
    with open(ruta, encoding="utf-8") as f:
        return {fila[0]: fila[1] for fila in csv.reader(f) if len(fila) >= 2}


def _modulos():
    return frappe.get_all("Module Def", filters={"app_name": APP}, pluck="name")


class IntegrationTestMigas(IntegrationTestCase):
    def test_cada_pantalla_del_sgc_tiene_nombre_humano(self):
        traducciones = _traducciones()
        sin_nombre = sorted(
            set(frappe.get_all("DocType", filters={"module": ["in", _modulos()], "istable": 0},
                               pluck="name"))
            - set(traducciones) - IGUALES_EN_ESPANOL
        )
        self.assertEqual(sin_nombre, [], "Pantallas que la miga pintaría con su nombre técnico: "
                         "añádalas a translations/es.csv o, si ya se escriben igual, a IGUALES_EN_ESPANOL")

    def test_cada_area_e_informe_tiene_nombre_humano(self):
        traducciones = _traducciones()
        for modulo, nombre in escritorio.areas().items():
            self.assertEqual(traducciones.get(modulo), nombre)
        for informe in frappe.get_all("Report", filters={"module": ["in", _modulos()],
                                                         "is_standard": "Yes"}, pluck="name"):
            self.assertIn(informe, traducciones, f"Informe sin nombre humano: {informe}")

    def test_cada_area_tiene_portada_y_menu_estandar(self):
        self.assertEqual(set(escritorio.areas()), set(_modulos()))
        for modulo, nombre in escritorio.areas().items():
            with self.subTest(area=modulo):
                ws = frappe.db.get_value("Workspace", modulo, ["module", "public", "standard"], as_dict=True)
                self.assertEqual((ws.module, ws.public, ws.standard), (modulo, 1, 1))
                menu = frappe.db.get_value("Sidebar", nombre, ["module", "app", "standard"], as_dict=True)
                self.assertEqual((menu.module, menu.app, menu.standard), (modulo, APP, 1))

    def test_la_portada_general_es_estandar(self):
        self.assertEqual(frappe.db.get_value("Workspace", escritorio.INICIO, "standard"), 1)

    def test_ninguna_pantalla_esta_en_dos_menus(self):
        donde = {}
        for modulo, menu in escritorio.menus().items():
            for _etiqueta, tipo, destino in escritorio.destinos(menu):
                if tipo in ("DocType", "Report"):
                    donde.setdefault(destino, []).append(modulo)
        self.assertEqual({d: m for d, m in donde.items() if len(m) > 1}, {})

    def test_no_queda_codigo_que_parchee_el_desk(self):
        """Lo que hacían migas.js y desk_home.js lo hace ahora Frappe con los ficheros estándar."""
        incluidos = " ".join(frappe.get_hooks("app_include_js", app_name=APP) or [])
        self.assertNotIn("migas.js", incluidos)
        self.assertNotIn("desk_home.js", incluidos)

    def test_el_desk_entra_al_sgc(self):
        """Ajuste nativo de Frappe (System Settings → App por defecto), en lugar de desk_home.js."""
        from sgc.patches import app_por_defecto

        app_por_defecto.execute()
        self.assertEqual(frappe.db.get_single_value("System Settings", "default_app"), APP)
