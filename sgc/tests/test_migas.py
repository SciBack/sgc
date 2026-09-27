# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Migas de pan coherentes en el Desk (revisión del 27-sep-2026).

La miga de una pantalla del SGC debe ser  ⌂ > Área > Pantalla > Registro  venga de
donde venga. Lo que la decide en el servidor, y que se prueba aquí:

  - cada pantalla, área e informe tiene nombre humano en `translations/es.csv`
    (sin él, la miga pinta el nombre técnico sin tilde: «Accion Mejora»);
  - cada área tiene su portada (Workspace), su barra lateral con `app = "sgc"` y su
    icono de miga enlazado a la portada;
  - ninguna pantalla está en dos barras: si lo está, Frappe elige la barra por
    historial y la misma pantalla da migas distintas según el camino.

Lo que ocurre en el navegador (el orden en que se dibuja la miga) lo cubre
`sgc/public/js/migas.js` y se comprobó recorriendo las 55 pantallas en el lab.
"""

import csv
import os

import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f18_workspace

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
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        f18_workspace.run()

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
        for modulo in f18_workspace.AREAS:
            self.assertEqual(traducciones.get(modulo), f18_workspace.AREAS[modulo][0])
        for informe in frappe.get_all("Report", filters={"module": ["in", _modulos()],
                                                         "is_standard": "Yes"}, pluck="name"):
            self.assertIn(informe, traducciones, f"Informe sin nombre humano: {informe}")

    def test_cada_area_tiene_portada_barra_e_icono(self):
        for modulo in f18_workspace.AREAS:
            with self.subTest(area=modulo):
                ws = frappe.db.get_value("Workspace", modulo, ["module", "public"], as_dict=True)
                self.assertIsNotNone(ws, "sin portada de área")
                self.assertEqual((ws.module, ws.public), (modulo, 1))
                self.assertEqual(frappe.db.get_value("Workspace Sidebar", modulo, "app"), APP)
                self.assertEqual(
                    frappe.db.get_value("Desktop Icon", {"label": modulo}, "link"),
                    f18_workspace.ruta_area(modulo),
                )

    def test_ninguna_pantalla_esta_en_dos_barras(self):
        barras = list(f18_workspace.SIDEBARS)
        donde = {}
        for barra in barras:
            for destino in frappe.get_all("Workspace Sidebar Item",
                                          filters={"parent": barra, "link_type": ["in", ["DocType", "Report"]]},
                                          pluck="link_to"):
                donde.setdefault(destino, []).append(barra)
        repetidas = {d: b for d, b in donde.items() if len(b) > 1}
        self.assertEqual(repetidas, {})

    def test_la_barra_general_solo_navega_entre_areas(self):
        destinos = frappe.get_all("Workspace Sidebar Item", filters={"parent": f18_workspace.WS},
                                  fields=["link_type", "link_to"])
        self.assertTrue(destinos)
        self.assertEqual({d.link_type for d in destinos}, {"Workspace"})
        self.assertEqual({d.link_to for d in destinos} - {f18_workspace.WS}, set(f18_workspace.AREAS))
