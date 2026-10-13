# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Alta de institución en un comando (#49): `sgc.setup.alta_institucion`.

El arranque común (los 29 pasos del despliegue, que confirman cada uno) y la escritura del
`site_config.json` se sustituyen por dobles: lo que se prueba aquí es el ORDEN, la validación
previa y la parada en un paso que falla; cada paso real tiene sus propios tests. La estructura
sí se importa de verdad, dentro de un savepoint que se deshace, sobre un sitio sin estructura.
"""

import contextlib
import io
import os
import shutil
import tempfile
from unittest.mock import patch

import frappe
import yaml
from frappe.tests import IntegrationTestCase

from sgc.setup import alta_institucion as alta
from sgc.setup import importador_estructura

SAVEPOINT = "alta_institucion"
ENTORNO = {"SGC_PRUEBA_SECRETO": "secreto-de-prueba-que-no-debe-salir"}


def _perfil(**cambios):
    perfil = {
        "institucion": {"nombre": "Universidad de Prueba", "sistema": "SGC de Prueba"},
        "identidad_digital": {"issuer": "https://idp.example.org/realms/prueba", "client_id": "sgc-prueba",
                              "proveedor": "sgc_prueba_alta", "client_secret_env": "SGC_PRUEBA_SECRETO"},
        "pais": {"marcos": []},
        "estructura": importador_estructura.PLANTILLAS,
    }
    for bloque, valor in cambios.items():
        if valor is None:
            perfil.pop(bloque, None)
        else:
            perfil[bloque] = valor
    return perfil


class _Base(IntegrationTestCase):
    def setUp(self):
        frappe.db.savepoint(SAVEPOINT)
        self.addCleanup(frappe.db.rollback, save_point=SAVEPOINT)
        for doctype in ("Programa Sede", "Programa", "Periodo Academico", "Unidad Organica"):
            frappe.db.delete(doctype)
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _errores(self, perfil, entorno=ENTORNO):
        with self.assertRaises(alta.PerfilInvalido) as e:
            alta.preparar(perfil, self.tmp, entorno=entorno, conf={})
        return e.exception.errores


class IntegrationTestPerfil(_Base):
    def test_un_perfil_completo_se_traduce_a_configuracion(self):
        plan = alta.preparar(_perfil(), self.tmp, entorno=ENTORNO, conf={})
        self.assertEqual(plan["config"]["sgc_institucion"], "Universidad de Prueba")
        self.assertEqual(plan["config"]["sgc_sso_client_id"], "sgc-prueba")
        self.assertEqual(plan["config"]["sgc_marcos"], [])
        self.assertEqual(plan["secreto"], ENTORNO["SGC_PRUEBA_SECRETO"])
        self.assertNotIn("sgc_sso_client_secret", plan["config"])  # el secreto viaja aparte

    def test_el_ejemplo_del_producto_es_valido(self):
        ejemplo = os.path.join(os.path.dirname(alta.__file__), "perfil-institucion.ejemplo.yaml")
        plan = alta.preparar(alta.leer(ejemplo), os.path.dirname(ejemplo),
                             entorno={"SGC_SSO_CLIENT_SECRET": "x"}, conf={})
        self.assertEqual(plan["config"]["sgc_marcos"], ["coneau-programas-2025"])
        self.assertTrue(plan["estructura"].endswith(os.path.join("plantillas", "estructura")))

    def test_sin_nombre_de_institucion_se_rechaza(self):
        errores = self._errores(_perfil(institucion={"sistema": "SGC"}))
        self.assertTrue(any("institucion.nombre" in e for e in errores))

    def test_el_secreto_nunca_va_en_el_perfil(self):
        sso = {**_perfil()["identidad_digital"], "client_secret": "en-claro"}
        errores = self._errores(_perfil(identidad_digital=sso))
        self.assertTrue(any("client_secret no va en el perfil" in e for e in errores))
        self.assertFalse(any("en-claro" in e for e in errores))

    def test_la_variable_del_secreto_tiene_que_existir(self):
        errores = self._errores(_perfil(), entorno={})
        self.assertTrue(any("SGC_PRUEBA_SECRETO" in e for e in errores))

    def test_un_marco_que_no_existe(self):
        errores = self._errores(_perfil(pais={"marcos": ["no-existe"]}))
        self.assertTrue(any("pais.marcos" in e and "no-existe" in e for e in errores))

    def test_una_estructura_rota_se_rechaza_antes_de_escribir(self):
        estructura = os.path.join(self.tmp, "estructura")
        shutil.copytree(importador_estructura.PLANTILLAS, estructura)
        with open(os.path.join(estructura, "unidades.csv"), "a", encoding="utf-8") as fh:
            fh.write("EJ-HUERFANA,Huérfana,Oficina,NO-EXISTE,,0\n")
        errores = self._errores(_perfil(estructura=estructura))
        self.assertTrue(any(e.startswith("estructura:") and "NO-EXISTE" in e for e in errores))

    def test_todo_lo_que_falta_se_dice_junto(self):
        errores = self._errores({"institucion": {}, "pais": {"marcos": ["no-existe"]}, "colores": {}}, entorno={})
        self.assertGreaterEqual(len(errores), 3)


class IntegrationTestAlta(_Base):
    def _escribir_perfil(self, perfil):
        ruta = os.path.join(self.tmp, "perfil.yaml")
        with open(ruta, "w", encoding="utf-8") as fh:
            yaml.safe_dump(perfil, fh, allow_unicode=True)
        return ruta

    @contextlib.contextmanager
    def _entorno(self, arranque=None):
        """site_config solo en memoria, arranque común simulado, sin commits."""
        self.escritas, self.arranques = [], []

        def _arranque():
            self.arranques.append(1)
            if arranque:
                arranque()

        sin_claves = {k: None for k in frappe.local.conf if k.startswith("sgc_")}
        with patch.dict(frappe.local.conf, sin_claves), patch.dict(os.environ, ENTORNO), \
                patch("frappe.installer.update_site_config", side_effect=lambda k, v: self.escritas.append(k)), \
                patch.object(alta, "_arranque_comun", side_effect=_arranque), \
                patch.object(frappe.db, "commit"), contextlib.redirect_stdout(io.StringIO()) as salida:
            for k in [k for k, v in frappe.local.conf.items() if k.startswith("sgc_") and v is None]:
                frappe.local.conf.pop(k)
            yield salida

    def test_alta_completa_configura_arranca_importa_y_verifica(self):
        with self._entorno():
            hallazgos = alta.alta(self._escribir_perfil(_perfil()))
        self.assertIn("sgc_institucion", self.escritas)
        self.assertIn("sgc_sso_client_secret", self.escritas)
        self.assertEqual(self.arranques, [1])
        self.assertEqual(frappe.db.count("Unidad Organica"), 7)
        codigos = {h["codigo"] for h in hallazgos}
        self.assertNotIn("sin-estructura", codigos)
        self.assertNotIn("sin-periodo-vigente", codigos)

    def test_reejecutar_no_duplica_ni_reescribe(self):
        ruta = self._escribir_perfil(_perfil())
        with self._entorno():
            alta.alta(ruta)
            primeras = list(self.escritas)
            modificados = dict(frappe.get_all("Unidad Organica", fields=["name", "modified"], as_list=True))
            alta.alta(ruta)
        self.assertEqual(self.escritas, primeras)  # la segunda vez no cambia ninguna clave
        self.assertEqual(dict(frappe.get_all("Unidad Organica", fields=["name", "modified"], as_list=True)),
                         modificados)

    def test_un_perfil_invalido_no_escribe_nada(self):
        with self._entorno(), self.assertRaises(alta.PerfilInvalido):
            alta.alta(self._escribir_perfil(_perfil(institucion={})))
        self.assertEqual((self.escritas, self.arranques), ([], []))
        self.assertEqual(frappe.db.count("Unidad Organica"), 0)

    def test_un_paso_que_falla_detiene_el_alta_y_lo_nombra(self):
        def _falla():
            raise alta.PasoFallido("arranque común, paso f3b_rbac: fallo simulado")

        with self._entorno(arranque=_falla), self.assertRaises(alta.PasoFallido) as e:
            alta.alta(self._escribir_perfil(_perfil()))
        self.assertIn("f3b_rbac", str(e.exception))
        self.assertEqual(frappe.db.count("Unidad Organica"), 0)  # la estructura no llegó a importarse

    def test_el_comando_termina_con_codigo_1_si_no_puede_empezar(self):
        with self._entorno() as salida, self.assertRaises(SystemExit) as fin:
            alta.run(self._escribir_perfil(_perfil(institucion={})))
        self.assertEqual(fin.exception.code, 1)
        self.assertIn("Alta NO iniciada", salida.getvalue())

    def test_el_comando_dice_en_que_paso_se_detuvo(self):
        def _falla():
            raise alta.PasoFallido("arranque común, paso f5_workflow_documental: fallo simulado")

        with self._entorno(arranque=_falla) as salida, self.assertRaises(SystemExit) as fin:
            alta.run(self._escribir_perfil(_perfil()))
        self.assertEqual(fin.exception.code, 1)
        self.assertIn("DETENIDA en arranque común, paso f5_workflow_documental", salida.getvalue())
        self.assertNotIn(ENTORNO["SGC_PRUEBA_SECRETO"], salida.getvalue())
