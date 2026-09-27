# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Análisis de causas con metodología estructurada (#34, ISO 9001 §10.2.1 b).

  Al PASAR a tratamiento una NC que requiere análisis:
    - sin metodología, sin causas o sin causa raíz se rechaza, diciendo qué falta
    - cada causa trae el dato de su metodología (nivel, categoría, frecuencia)
    - con el análisis completo pasa, con cada metodología
  Lo que no cambia:
    - una NC que no requiere análisis no pide nada de esto
    - una NC anterior a #34 ya en tratamiento sigue guardando y avanzando con texto
  Acción de mejora:
    - enlaza una causa de SU no conformidad y copia su descripción
    - una causa de otra no conformidad se rechaza

Todo se deshace al final de cada test (rollback de `IntegrationTestCase`).
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from sgc.tests import factories

ADMIN = "Administrator"
TEXTO = "Las actas se cargan a mano y nadie las revisa antes de publicar."


class IntegrationTestAnalisisCausas(IntegrationTestCase):
    def setUp(self):
        factories.desactivar_workflow("No Conformidad")
        factories.desactivar_workflow("Accion Mejora")

    def _nc_en_analisis(self, **overrides):
        vals = {
            "doctype": "No Conformidad",
            "titulo": "NC de prueba #34",
            "tipo": "No conformidad mayor",
            "estado": "En analisis",
            "responsable": ADMIN,
            "analisis_causa": TEXTO,
        }
        vals.update(overrides)
        return frappe.get_doc(vals).insert(ignore_permissions=True)

    def _a_tratamiento(self, nc):
        nc.estado = "En tratamiento"
        nc.save(ignore_permissions=True)
        return nc

    def _causa(self, nc, descripcion="Carga manual sin revisión", raiz=1, **extra):
        nc.append("causas", {"descripcion": descripcion, "es_causa_raiz": raiz, **extra})

    # -- lo que se exige ---------------------------------------------------------
    def test_sin_metodologia_no_pasa_a_tratamiento(self):
        nc = self._nc_en_analisis()
        self._causa(nc)
        with self.assertRaises(frappe.ValidationError) as ctx:
            self._a_tratamiento(nc)
        self.assertIn("metodología", str(ctx.exception))

    def test_sin_causas_no_pasa_a_tratamiento(self):
        nc = self._nc_en_analisis(metodologia="Lluvia de ideas")
        with self.assertRaises(frappe.ValidationError) as ctx:
            self._a_tratamiento(nc)
        self.assertIn("al menos una causa", str(ctx.exception))

    def test_sin_causa_raiz_no_pasa_y_lo_dice(self):
        nc = self._nc_en_analisis(metodologia="Lluvia de ideas")
        self._causa(nc, raiz=0)
        with self.assertRaises(frappe.ValidationError) as ctx:
            self._a_tratamiento(nc)
        self.assertIn("causa raíz", str(ctx.exception))

    def test_cinco_porques_exige_el_nivel_de_cada_causa(self):
        nc = self._nc_en_analisis(metodologia="Cinco porqués")
        self._causa(nc, "Las actas salen con errores", raiz=0, nivel=1)
        self._causa(nc, "Nadie las revisa", raiz=1)
        with self.assertRaises(frappe.ValidationError) as ctx:
            self._a_tratamiento(nc)
        self.assertIn("filas: 2", str(ctx.exception))

    def test_ishikawa_exige_la_categoria(self):
        nc = self._nc_en_analisis(metodologia="Espina de pescado (Ishikawa)")
        self._causa(nc)
        with self.assertRaises(frappe.ValidationError):
            self._a_tratamiento(nc)

    def test_pareto_exige_la_frecuencia(self):
        nc = self._nc_en_analisis(metodologia="Pareto")
        self._causa(nc)
        with self.assertRaises(frappe.ValidationError):
            self._a_tratamiento(nc)

    # -- con el análisis completo, cada metodología pasa ----------------------------
    def test_recorrido_completo_con_cada_metodologia(self):
        completas = {
            "Cinco porqués": [
                {"descripcion": "Las actas salen con errores", "nivel": 1},
                {"descripcion": "Se cargan a mano", "nivel": 2},
                {"descripcion": "No hay integración con el registro académico", "nivel": 3, "es_causa_raiz": 1},
            ],
            "Espina de pescado (Ishikawa)": [
                {"descripcion": "Docentes sin formación en el sistema", "categoria": "Personas"},
                {"descripcion": "No hay revisión previa", "categoria": "Método", "es_causa_raiz": 1},
            ],
            "Pareto": [
                {"descripcion": "Promedio mal ponderado", "frecuencia": 12, "es_causa_raiz": 1},
                {"descripcion": "Nota fuera de plazo", "frecuencia": 3},
            ],
            "Lluvia de ideas": [{"descripcion": "Falta de control previo", "es_causa_raiz": 1}],
        }
        for metodologia, causas in completas.items():
            with self.subTest(metodologia=metodologia):
                nc = self._nc_en_analisis(metodologia=metodologia)
                for c in causas:
                    nc.append("causas", c)
                self.assertEqual(self._a_tratamiento(nc).estado, "En tratamiento")

    # -- lo que no cambia -------------------------------------------------------------
    def test_sin_requerir_analisis_no_se_pide_nada(self):
        nc = self._nc_en_analisis(tipo="No conformidad menor", analisis_causa=None)
        self.assertFalse(nc.requiere_analisis_causa)
        self.assertEqual(self._a_tratamiento(nc).estado, "En tratamiento")

    def test_una_nc_anterior_a_34_sigue_guardando_y_avanzando(self):
        """La tabla vacía es válida para lo que ya estaba en tratamiento."""
        nc = frappe.get_doc({
            "doctype": "No Conformidad", "titulo": "NC antigua", "tipo": "No conformidad mayor",
            "estado": "En tratamiento", "responsable": ADMIN, "analisis_causa": TEXTO,
        }).insert(ignore_permissions=True)
        nc.correccion_inmediata = "Se reemitieron las actas."
        nc.save(ignore_permissions=True)
        nc.estado = "En verificacion"
        nc.fecha_compromiso = add_days(nowdate(), 10)
        nc.save(ignore_permissions=True)
        self.assertEqual(nc.estado, "En verificacion")
        self.assertEqual(nc.causas, [])

    # -- acción ligada a causa ----------------------------------------------------------
    def _accion(self, nc, **extra):
        vals = {
            "doctype": "Accion Mejora", "descripcion": "Revisión previa de actas", "tipo": "Correctiva",
            "estado": "Planificada", "responsable": ADMIN, "no_conformidad": nc,
            "fecha_compromiso": add_days(nowdate(), 30),
        }
        vals.update(extra)
        return frappe.get_doc(vals).insert(ignore_permissions=True)

    def _nc_con_causa(self):
        nc = self._nc_en_analisis(metodologia="Lluvia de ideas")
        self._causa(nc, "No hay revisión previa de actas")
        nc.save(ignore_permissions=True)
        return nc

    def test_la_accion_enlaza_una_causa_de_su_nc(self):
        nc = self._nc_con_causa()
        accion = self._accion(nc.name, causa=nc.causas[0].name)
        self.assertEqual(accion.causa_descripcion, "No hay revisión previa de actas")

    def test_una_causa_de_otra_nc_se_rechaza(self):
        propia = self._nc_con_causa()
        otra = self._nc_con_causa()
        with self.assertRaises(frappe.ValidationError) as ctx:
            self._accion(propia.name, causa=otra.causas[0].name)
        self.assertIn("no pertenece", str(ctx.exception))

    def test_una_causa_inexistente_se_rechaza(self):
        nc = self._nc_con_causa()
        with self.assertRaises(frappe.ValidationError):
            self._accion(nc.name, causa="no-existe")

    def test_sin_causa_la_accion_no_cambia(self):
        nc = self._nc_con_causa()
        self.assertIsNone(self._accion(nc.name).causa_descripcion)
