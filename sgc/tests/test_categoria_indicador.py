# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Tests de F20 — la categoría `Acreditacion` tiene que respaldarla el marco.

`categoria` es filtro estándar en la lista de Indicador, así que es lo primero que
alguien pulsa para ver «los de acreditación». En producción devolvía exactamente lo
contrario de lo que promete: los cinco marcados así eran conteos operativos de
MidPoint sin marco normativo, y los del modelo Coneau figuraban como `Proceso`.

El criterio que se prueba aquí: **`categoria` es la naturaleza del dato; acreditar
lo declara `marco_normativo`.** Un indicador que dice `Acreditacion` sin un marco de
acreditación detrás se recoloca en `Gestion`. Si el marco sí acredita, se respeta —
el paso corrige lo que no se sostiene, no impone una etiqueta.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f20_categoria_indicador as f20
from sgc.tests import factories


class IntegrationTestCategoriaIndicador(IntegrationTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def _categoria(self, nombre):
        return frappe.db.get_value("Indicador", nombre, "categoria")

    def test_sin_marco_no_puede_decir_que_acredita(self):
        ind = factories.crear_indicador(categoria="Acreditacion").name
        f20.run()
        self.assertEqual(self._categoria(ind), "Gestion", "un conteo sin marco no acredita nada")

    def test_con_marco_de_acreditacion_se_respeta(self):
        marco = factories.crear_marco_prueba(n_estandares=1, n_criterios=1)["marco"]
        if not frappe.get_meta("Marco Normativo").has_field("alcance"):
            self.skipTest("el campo `alcance` aún no existe en este sitio")
        frappe.db.set_value("Marco Normativo", marco, "alcance", "Acreditación de programa")
        ind = factories.crear_indicador(categoria="Acreditacion", marco_normativo=marco).name
        f20.run()
        self.assertEqual(self._categoria(ind), "Acreditacion", "su marco lo respalda: no se toca")

    def test_no_toca_las_demas_categorias(self):
        proceso = factories.crear_indicador(categoria="Proceso").name
        satisf = factories.crear_indicador(categoria="Satisfaccion").name
        f20.run()
        self.assertEqual(self._categoria(proceso), "Proceso")
        self.assertEqual(self._categoria(satisf), "Satisfaccion")

    def test_es_idempotente(self):
        factories.crear_indicador(categoria="Acreditacion")
        f20.run()
        segunda = f20.run()
        self.assertEqual(segunda["cambios"], [], "un sitio ya corregido no se vuelve a escribir")

    def test_corre_en_cada_despliegue(self):
        # Los MP-* los escribe un conector externo: corregir la base una sola vez no
        # impide que vuelvan a llegar mal etiquetados.
        from sgc.setup import f_deploy_run_all

        nombres = [n for n, _ in f_deploy_run_all.STEPS]
        self.assertIn("f20_categoria_indicador", nombres)
