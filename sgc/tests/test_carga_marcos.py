# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Marcos normativos declarados por la instancia (#47): `sgc.setup.marcos_normativos`.

Se carga un marco de PRUEBA (`datos/marco-prueba.yaml`), nunca el CONEAU: así la prueba no
depende de que el sitio lo tenga o no, y sus códigos `TEST-MARCO-CARGA*` no chocan con nada.
Todo corre dentro de un savepoint que se deshace (la carga se llama con `commit=False`).
"""

import contextlib
import io
import os
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f2_load_coneau, marcos_normativos
from sgc.setup.f_deploy_run_all import STEPS

YAML_PRUEBA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos", "marco-prueba.yaml")
MARCO = "TEST-MARCO-CARGA"
SAVEPOINT = "carga_marcos"


class TestPerfilDeclarado(IntegrationTestCase):
    """La lectura del perfil: sin tocar la base."""

    def test_sin_declaracion_no_hay_nada_que_cargar(self):
        for conf in ({}, {"sgc_marcos": None}, {"sgc_marcos": []}, {"sgc_marcos": ""}):
            self.assertEqual(marcos_normativos.declarados(conf), [])

    def test_un_marco_del_producto_se_declara_por_nombre(self):
        rutas = marcos_normativos.declarados({"sgc_marcos": ["coneau-programas-2025"]})
        self.assertEqual(len(rutas), 1)
        self.assertTrue(rutas[0].endswith(os.path.join("marcos", "coneau-programas-2025.yaml")))
        self.assertIn("coneau-programas-2025", marcos_normativos.disponibles())

    def test_un_yaml_propio_se_declara_por_ruta(self):
        self.assertEqual(marcos_normativos.declarados({"sgc_marcos": [YAML_PRUEBA]}), [YAML_PRUEBA])

    def test_un_nombre_que_no_existe_se_rechaza_y_lista_los_disponibles(self):
        with self.assertRaises(marcos_normativos.PerfilInvalido) as e:
            marcos_normativos.declarados({"sgc_marcos": ["coneau-programas-2025", "no-existe"]})
        self.assertIn("no-existe", str(e.exception))
        self.assertIn("coneau-programas-2025", str(e.exception))

    def test_un_valor_que_no_es_lista_se_rechaza(self):
        with self.assertRaises(marcos_normativos.PerfilInvalido):
            marcos_normativos.declarados({"sgc_marcos": {"marco": "x"}})

    def test_los_codigos_salen_del_yaml(self):
        cfg = f2_load_coneau.configuracion(f2_load_coneau._load_yaml(
            marcos_normativos.resolver("coneau-programas-2025")))
        # Los de las instancias que ya lo cargaron: cambiarlos duplicaría la carga.
        self.assertEqual((cfg["marco"], cfg["escala"], cfg["ente"], cfg["prefijo_elementos"], cfg["prefijo_indicadores"]),
                         ("CONEAU-Programas-2025", "CONEAU-NLLP", "SINEACE", "CONEAU", ""))

    def test_el_arranque_comun_ya_no_carga_ningun_marco(self):
        self.assertIn("marcos_normativos", [nombre for nombre, _ in STEPS])


class IntegrationTestCargaDeMarcos(IntegrationTestCase):
    def setUp(self):
        frappe.db.savepoint(SAVEPOINT)
        self.addCleanup(frappe.db.rollback, save_point=SAVEPOINT)

    def _cargar(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return f2_load_coneau.run(YAML_PRUEBA, commit=False)

    def _run_paso(self, conf):
        salida = io.StringIO()
        with patch.dict(frappe.local.conf, {"sgc_marcos": None, **conf}), contextlib.redirect_stdout(salida), \
                patch.object(f2_load_coneau.frappe.db, "commit"):
            resultado = marcos_normativos.run()
        return resultado, salida.getvalue()

    def _conteos(self):
        return {
            "marco": frappe.db.count("Marco Normativo", {"name": MARCO}),
            "escala": frappe.db.count("Escala Valoracion", {"name": "TEST-MARCO-CARGA-ESC"}),
            "niveles": frappe.db.count("Nivel Escala", {"parent": "TEST-MARCO-CARGA-ESC"}),
            "elementos": frappe.db.count("Elemento Marco", {"marco_normativo": MARCO}),
            "indicadores": frappe.db.count("Indicador", {"marco_normativo": MARCO}),
            "fichas": frappe.db.count("Ficha Indicador", {"indicador": ["like", f"{MARCO}-ID%"]}),
            "vinculos": frappe.db.count("Indicador Criterio", {"parent": ["like", f"{MARCO}-ID%"]}),
        }

    def test_la_carga_puebla_los_siete_doctypes(self):
        self._cargar()
        self.assertEqual(self._conteos(), {"marco": 1, "escala": 1, "niveles": 3, "elementos": 4,
                                           "indicadores": 2, "fichas": 2, "vinculos": 2})

    def test_los_codigos_llevan_el_prefijo_del_marco(self):
        self._cargar()
        self.assertTrue(frappe.db.exists("Elemento Marco", f"{MARCO}-E1.1"))
        self.assertTrue(frappe.db.exists("Indicador", f"{MARCO}-ID1"))
        niveles = frappe.get_all("Nivel Escala", filters={"parent": "TEST-MARCO-CARGA-ESC"},
                                 fields=["sigla", "etiqueta"], order_by="score asc")
        self.assertEqual([n.sigla for n in niveles], ["NL", "L", "LP"])
        self.assertEqual(niveles[0].etiqueta, "No logrado")

    def test_reejecutar_no_duplica_ni_altera(self):
        self._cargar()
        antes = self._conteos()
        modificado = frappe.db.get_value("Marco Normativo", MARCO, "modified")
        contadores = self._cargar()
        self.assertEqual(self._conteos(), antes)
        self.assertEqual(frappe.db.get_value("Marco Normativo", MARCO, "modified"), modificado)
        self.assertEqual((contadores["marcos"], contadores["elementos"], contadores["indicadores"], contadores["links"]),
                         (0, 0, 0, 0))

    def test_sin_declaracion_el_paso_no_carga_nada_y_lo_dice(self):
        antes = frappe.db.count("Marco Normativo")
        resultado, salida = self._run_paso({})
        self.assertEqual(resultado, "sin-declarar")
        self.assertIn("ninguno declarado", salida)
        self.assertEqual(frappe.db.count("Marco Normativo"), antes)

    def test_un_marco_ya_cargado_se_conserva_al_dejar_de_declararlo(self):
        self._cargar()
        frappe.db.set_value("Marco Normativo", MARCO, "nota_normativa", "editada a mano")
        self._run_paso({})
        self.assertEqual(self._conteos()["elementos"], 4)
        self.assertEqual(frappe.db.get_value("Marco Normativo", MARCO, "nota_normativa"), "editada a mano")

    def test_declarado_el_paso_lo_carga(self):
        resultado, _ = self._run_paso({"sgc_marcos": [YAML_PRUEBA]})
        self.assertEqual(resultado, "cargados")
        self.assertEqual(self._conteos()["indicadores"], 2)

    def test_con_una_entrada_mala_no_carga_ninguna(self):
        resultado, salida = self._run_paso({"sgc_marcos": [YAML_PRUEBA, "no-existe"]})
        self.assertEqual(resultado, "invalido")
        self.assertIn("no-existe", salida)
        self.assertEqual(self._conteos()["marco"], 0)
