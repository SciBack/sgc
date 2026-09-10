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
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f20_categoria_indicador as f20
from sgc.tests import factories


class IntegrationTestCategoriaIndicador(IntegrationTestCase):
    """⚠️ `f20.run()` hace `frappe.db.commit()`, así que lo que estos tests toquen
    SOBREVIVE al rollback de la clase y queda en la base para el resto de la suite.

    De ahí las dos precauciones de abajo, que no son manía:

    - **No se toca ningún objeto compartido.** La primera versión le ponía `alcance`
      al marco de `crear_marco_prueba`, que es idempotente y lo reutiliza media
      suite: el commit lo dejaba declarado como acreditación de programa y, a
      partir de ahí, cualquier test que abriera una autoevaluación sin
      programa-sede reventaba con «Este marco acredita un programa de estudios».
      Se comprobó en CI, no en local, porque corriendo el módulo suelto no se ve.
      Para el caso del marco que sí acredita se sustituye `es_de_acreditacion`, que
      es justo lo que F20 consulta.
    - **Se borra lo creado.** El rollback no alcanza a lo comiteado, así que la
      limpieza es explícita.
    """

    def setUp(self):
        frappe.set_user("Administrator")
        self.creados = []

    def tearDown(self):
        for nombre in self.creados:
            if frappe.db.exists("Indicador", nombre):
                frappe.delete_doc("Indicador", nombre, force=1, ignore_permissions=True)
        frappe.db.commit()

    def _indicador(self, **kwargs):
        ind = factories.crear_indicador(**kwargs).name
        self.creados.append(ind)
        return ind

    def _categoria(self, nombre):
        return frappe.db.get_value("Indicador", nombre, "categoria")

    def test_sin_marco_no_puede_decir_que_acredita(self):
        ind = self._indicador(categoria="Acreditacion")
        f20.run()
        self.assertEqual(self._categoria(ind), "Gestion", "un conteo sin marco no acredita nada")

    def test_con_marco_de_acreditacion_se_respeta(self):
        ind = self._indicador(categoria="Acreditacion")
        with patch.object(f20.marcos, "es_de_acreditacion", return_value=True):
            f20.run()
        self.assertEqual(self._categoria(ind), "Acreditacion", "su marco lo respalda: no se toca")

    def test_no_toca_las_demas_categorias(self):
        proceso = self._indicador(categoria="Proceso")
        satisf = self._indicador(categoria="Satisfaccion")
        f20.run()
        self.assertEqual(self._categoria(proceso), "Proceso")
        self.assertEqual(self._categoria(satisf), "Satisfaccion")

    def test_es_idempotente(self):
        self._indicador(categoria="Acreditacion")
        f20.run()
        segunda = f20.run()
        self.assertEqual(segunda["cambios"], [], "un sitio ya corregido no se vuelve a escribir")

    def test_corre_en_cada_despliegue(self):
        # Los MP-* los escribe un conector externo: corregir la base una sola vez no
        # impide que vuelvan a llegar mal etiquetados.
        from sgc.setup import f_deploy_run_all

        nombres = [n for n, _ in f_deploy_run_all.STEPS]
        self.assertIn("f20_categoria_indicador", nombres)
