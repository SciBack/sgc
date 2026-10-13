# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Importador de la estructura institucional (#48): `sgc.setup.importador_estructura`.

La validación es pura y se prueba sin base. La importación corre dentro de un savepoint que
se deshace, sobre un sitio sin estructura (se borra dentro del savepoint), porque el árbol que
resulta debe tener una sola raíz y una copia de producción ya trae la suya.
"""

import csv
import os
import shutil
import tempfile
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import importador_estructura as imp

SAVEPOINT = "importador_estructura_test"


def _sitio_vacio(**extra):
    sitio = {"unidades": {}, "programas": set(), "opciones": {
        ("unidades", "tipo"): ["Universidad", "Sede", "Facultad", "Escuela", "Oficina"],
        ("periodos", "estado"): ["abierto", "cerrado"],
    }}
    sitio.update(extra)
    return sitio


def _u(fila, codigo, padre="", tipo="Oficina", **extra):
    return {"_fila": fila, "codigo": codigo, "nombre": f"Unidad {codigo}", "tipo": tipo, "padre": padre, **extra}


class TestValidacion(IntegrationTestCase):
    """Lo que decide si una hoja entra o no: sin tocar la base."""

    def test_los_hijos_antes_que_los_padres_se_reordenan(self):
        unidades = [_u(2, "NIETA", "HIJA"), _u(3, "HIJA", "RAIZ"), _u(4, "RAIZ", tipo="Universidad")]
        orden = [u["codigo"] for u in imp.ordenar_por_profundidad(unidades)]
        self.assertEqual(orden, ["RAIZ", "HIJA", "NIETA"])

    def test_el_padre_puede_estar_ya_en_el_sitio(self):
        orden = imp.ordenar_por_profundidad([_u(2, "NIETA", "HIJA"), _u(3, "HIJA", "RAIZ")], {"RAIZ": None})
        self.assertEqual([u["codigo"] for u in orden], ["HIJA", "NIETA"])

    def test_un_ciclo_se_detecta(self):
        with self.assertRaises(ValueError):
            imp.ordenar_por_profundidad([_u(2, "A", "B"), _u(3, "B", "A")])

    def test_un_padre_inexistente_nombra_la_fila_y_el_valor(self):
        errores = imp.validar({"unidades": [_u(2, "RAIZ", tipo="Universidad"), _u(3, "HIJA", "NO-EXISTE")]},
                              _sitio_vacio())
        self.assertEqual(len(errores), 1)
        self.assertIn("fila 3", errores[0])
        self.assertIn("NO-EXISTE", errores[0])

    def test_codigos_duplicados_se_rechazan(self):
        errores = imp.validar({"unidades": [_u(2, "RAIZ", tipo="Universidad"), _u(3, "RAIZ", tipo="Universidad")]},
                              _sitio_vacio())
        self.assertTrue(any("repetido" in e and "fila 3" in e for e in errores))

    def test_obligatorias_vacias_y_valores_fuera_de_lista(self):
        errores = imp.validar({"unidades": [{"_fila": 2, "codigo": "X", "nombre": "", "tipo": "Planeta", "padre": ""}]},
                              _sitio_vacio())
        self.assertTrue(any("falta «nombre»" in e for e in errores))
        self.assertTrue(any("Planeta" in e for e in errores))

    def test_mas_de_una_raiz_se_rechaza(self):
        errores = imp.validar({"unidades": [_u(2, "A", tipo="Universidad"), _u(3, "B", tipo="Universidad")]},
                              _sitio_vacio())
        self.assertTrue(any("2 raíces" in e for e in errores))

    def test_una_raiz_nueva_choca_con_la_del_sitio(self):
        sitio = _sitio_vacio(unidades={"YA": {"padre": None, "tipo": "Universidad"}})
        errores = imp.validar({"unidades": [_u(2, "OTRA", tipo="Universidad")]}, sitio)
        self.assertTrue(any("raíces" in e for e in errores))

    def test_la_sede_tiene_que_ser_de_tipo_sede(self):
        hojas = {"unidades": [_u(2, "RAIZ", tipo="Universidad"), _u(3, "OF", "RAIZ"), _u(4, "X", "RAIZ", sede="OF")]}
        self.assertTrue(any("tipo Sede" in e for e in imp.validar(hojas, _sitio_vacio())))

    def test_fechas_al_reves_y_mal_escritas(self):
        hojas = {"periodos": [
            {"_fila": 2, "codigo": "P1", "fecha_inicio": "2026-08-01", "fecha_fin": "2026-03-01"},
            {"_fila": 3, "codigo": "P2", "fecha_inicio": "ayer"},
        ]}
        errores = imp.validar(hojas, _sitio_vacio())
        self.assertTrue(any("fila 2" in e and "anterior" in e for e in errores))
        self.assertTrue(any("fila 3" in e and "fecha" in e for e in errores))

    def test_un_programa_sede_sin_programa_conocido(self):
        hojas = {"programas-sede": [{"_fila": 2, "codigo": "PS", "programa": "NADA", "sede": "NADA"}]}
        errores = imp.validar(hojas, _sitio_vacio())
        self.assertTrue(any("programa «NADA»" in e for e in errores))
        self.assertTrue(any("«sede» = «NADA»" in e for e in errores))

    def test_columnas_desconocidas_se_nombran(self):
        errores = imp.validar({"periodos": [{"_fila": 2, "codigo": "P", "vigente": "si"}]}, _sitio_vacio())
        self.assertTrue(any("vigente" in e for e in errores))


class IntegrationTestImportacion(IntegrationTestCase):
    def setUp(self):
        frappe.db.savepoint(SAVEPOINT)
        self.addCleanup(frappe.db.rollback, save_point=SAVEPOINT)
        for doctype in ("Programa Sede", "Programa", "Periodo Academico", "Unidad Organica"):
            frappe.db.delete(doctype)
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _copia_plantillas(self):
        destino = os.path.join(self.tmp, "estructura")
        shutil.copytree(imp.PLANTILLAS, destino)
        return destino

    def _conteos(self):
        return {d: frappe.db.count(d) for d in ("Unidad Organica", "Programa", "Programa Sede", "Periodo Academico")}

    def test_las_plantillas_se_importan_tal_cual(self):
        resultado = imp.importar(imp.PLANTILLAS, aplicar=True)
        self.assertEqual(self._conteos(),
                         {"Unidad Organica": 7, "Programa": 1, "Programa Sede": 2, "Periodo Academico": 2})
        self.assertEqual(resultado["unidades"]["creados"], 7)
        self.assertEqual(frappe.db.get_value("Unidad Organica", "EJ-EP-SIS", "parent_unidad_organica"), "EJ-FAC-ING")
        self.assertEqual(frappe.db.get_value("Periodo Academico", {"estado": "abierto"}, "name"), "EJ-2026-II")

    def test_el_arbol_resultante_es_coherente(self):
        imp.importar(imp.PLANTILLAS, aplicar=True)
        self.assertEqual(imp.comprobar_arbol(), [])

    def test_hijos_antes_que_padres_en_la_hoja(self):
        ruta = self._copia_plantillas()
        fichero = os.path.join(ruta, "unidades.csv")
        with open(fichero, encoding="utf-8") as fh:
            filas = list(csv.reader(fh))
        with open(fichero, "w", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerows([filas[0], *reversed(filas[1:])])
        imp.importar(ruta, aplicar=True)
        self.assertEqual(frappe.db.count("Unidad Organica"), 7)
        self.assertEqual(imp.comprobar_arbol(), [])

    def test_reimportar_no_duplica_ni_cambia_nada(self):
        imp.importar(imp.PLANTILLAS, aplicar=True)
        modificado = frappe.db.get_value("Unidad Organica", "EJ-FAC-ING", "modified")
        resultado = imp.importar(imp.PLANTILLAS, aplicar=True)
        self.assertEqual(self._conteos()["Unidad Organica"], 7)
        self.assertTrue(all(c["creados"] == 0 and c["actualizados"] == 0 for c in resultado.values()), resultado)
        self.assertEqual(frappe.db.get_value("Unidad Organica", "EJ-FAC-ING", "modified"), modificado)

    def test_reimportar_actualiza_por_codigo(self):
        imp.importar(imp.PLANTILLAS, aplicar=True)
        ruta = self._copia_plantillas()
        fichero = os.path.join(ruta, "unidades.csv")
        with open(fichero, encoding="utf-8") as fh:
            texto = fh.read().replace("Facultad de Ingeniería,", "Facultad de Ingeniería y Arquitectura,")
        with open(fichero, "w", encoding="utf-8") as fh:
            fh.write(texto)
        resultado = imp.importar(ruta, aplicar=True)
        self.assertEqual(resultado["unidades"]["actualizados"], 1)
        self.assertEqual(frappe.db.get_value("Unidad Organica", "EJ-FAC-ING", "nombre"),
                         "Facultad de Ingeniería y Arquitectura")

    def test_un_padre_inexistente_no_importa_ninguna_fila(self):
        ruta = self._copia_plantillas()
        with open(os.path.join(ruta, "unidades.csv"), "a", encoding="utf-8") as fh:
            fh.write("EJ-HUERFANA,Unidad huérfana,Oficina,NO-EXISTE,,0\n")
        with self.assertRaises(imp.EstructuraInvalida) as e:
            imp.importar(ruta, aplicar=True)
        self.assertIn("fila 9", str(e.exception))
        self.assertIn("NO-EXISTE", str(e.exception))
        self.assertEqual(sum(self._conteos().values()), 0)

    def test_un_error_a_mitad_no_deja_nada_escrito(self):
        original = imp._escribir
        llamadas = []

        def falla_en_la_cuarta(hoja, fila, extra=None):
            llamadas.append(fila["codigo"])
            if len(llamadas) == 4:
                raise RuntimeError("fallo simulado")
            return original(hoja, fila, extra)

        with patch.object(imp, "_escribir", falla_en_la_cuarta), self.assertRaises(imp.EstructuraInvalida) as e:
            imp.importar(imp.PLANTILLAS, aplicar=True)
        self.assertIn("fallo simulado", str(e.exception))
        self.assertEqual(sum(self._conteos().values()), 0)

    def test_sin_aplicar_valida_y_no_guarda(self):
        resultado = imp.importar(imp.PLANTILLAS, aplicar=False)
        self.assertEqual(resultado["unidades"]["creados"], 7)
        self.assertEqual(sum(self._conteos().values()), 0)

    def test_un_xlsx_con_las_mismas_hojas(self):
        from openpyxl import Workbook

        libro = Workbook()
        libro.remove(libro.active)
        for hoja in imp.HOJAS:
            with open(os.path.join(imp.PLANTILLAS, f"{hoja}.csv"), encoding="utf-8") as fh:
                ws = libro.create_sheet(hoja)
                for fila in csv.reader(fh):
                    ws.append(fila)
        ruta = os.path.join(self.tmp, "estructura.xlsx")
        libro.save(ruta)
        imp.importar(ruta, aplicar=True)
        self.assertEqual(self._conteos()["Programa Sede"], 2)
