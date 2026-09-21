# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `limit=0` — «sin límite», no «ningún resultado» (#69).

`limit_page_length` está deprecado y desaparece en Frappe v17. Sustituirlo por
`limit` parecía mecánico, pero **diez de los quince usos eran `limit_page_length=0`**,
que significa «tráelo todo»: si `limit=0` se interpretara como «cero resultados»,
los cuadros de mando pasarían a contar 0 **sin fallar**, que es la peor forma de
romperse — nadie mira un panel que dice cero, cree que no hay datos.

La cadena real, verificada en el source de Frappe 16:

- `db_query.py:166` — `if limit:` es una comprobación *falsy*: `limit=0` no se asigna.
- `db_query.py:187` — `cint(limit_page_length) if limit_page_length else None`: el 0
  se convierte en `None`.
- `db_query.py:1281-1284` — sin `limit_page_length`, **no se añade cláusula LIMIT**.

O sea: `limit=0` y `limit_page_length=0` acaban en el mismo sitio. Estos tests fijan
esa semántica contra la base real, para que si v17 la cambia nos enteremos por un
test en rojo y no por un panel en cero.
"""
import subprocess
from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase

# Hace falta un doctype con bastantes más de 20 filas para que «todos» y «una página»
# sean distinguibles a simple vista. `DocType` siempre las tiene.
DOCTYPE_CON_MUCHAS_FILAS = "DocType"


class IntegrationTestLimiteSinLimite(IntegrationTestCase):
    def test_get_all_no_pagina_por_defecto(self):
        """`get_all` fuerza `limit_page_length=0`, aunque su docstring diga «Default 20».

        Verificado en `frappe/__init__.py:1403-1404`. El docstring dice otra cosa, y
        de ahí viene la creencia —extendida, y en una memoria de este proyecto— de
        que `get_all` trunca a 20. Con `get_list` sí hay que tener cuidado; con
        `get_all` de Frappe 16.32, no.
        """
        filas = frappe.get_all(DOCTYPE_CON_MUCHAS_FILAS)

        self.assertGreater(len(filas), 20)

    def test_limit_cero_devuelve_todo_no_nada(self):
        con_cero = frappe.get_all(DOCTYPE_CON_MUCHAS_FILAS, limit=0)

        self.assertGreater(
            len(con_cero), 20,
            "limit=0 debe significar «sin límite»; si devuelve 0, la semántica cambió",
        )

    def test_limit_cero_equivale_al_deprecado(self):
        """Lo que se quiere probar del cambio: que sustituir no cambió el resultado."""
        total_conocido = frappe.db.count(DOCTYPE_CON_MUCHAS_FILAS)

        self.assertEqual(len(frappe.get_all(DOCTYPE_CON_MUCHAS_FILAS, limit=0)), total_conocido)

    def test_un_limite_normal_sigue_limitando(self):
        # Que «0 es todo» no se lleve por delante el caso corriente.
        self.assertEqual(len(frappe.get_all(DOCTYPE_CON_MUCHAS_FILAS, limit=3)), 3)

    # --- regresión sobre el propio repo ------------------------------------

    def test_el_codigo_ya_no_usa_el_parametro_deprecado(self):
        """Impide que vuelva a colarse: en v17 dejaría de funcionar.

        Se mira el código fuente y no un import, porque el parámetro puede
        reaparecer en cualquier fichero nuevo y el test debe verlo igual.
        """
        raiz = Path(frappe.get_app_path("sgc"))
        hallazgos = subprocess.run(
            ["grep", "-rn", "limit_page_length", "--include=*.py", str(raiz)],
            capture_output=True,
            text=True,
        ).stdout.strip()
        # El propio docstring de este fichero lo nombra; se excluye.
        lineas = [
            linea for linea in hallazgos.splitlines()
            if "test_limite_sin_limite.py" not in linea
        ]

        self.assertEqual(lineas, [], "usar `limit`; `limit_page_length` desaparece en v17")
