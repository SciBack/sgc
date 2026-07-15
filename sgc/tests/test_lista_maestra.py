# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de `sgc.lista_maestra` — export de la Lista Maestra de Documentos
Controlados a Excel (RF-B03/T06).

Cubre:
- `_filas_lista_maestra` devuelve una fila por Documento Controlado con las
  columnas de negocio, respeta el orden (proceso, código) y los filtros.
- El .xlsx generado con `make_xlsx` es un binario válido (firma ZIP `PK`).
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.xlsxutils import make_xlsx

from sgc.lista_maestra import _CABECERAS, _filas_lista_maestra
from sgc.tests import factories


class IntegrationTestListaMaestra(IntegrationTestCase):
    def setUp(self):
        # Un proceso propio + 2 documentos controlados de tipos distintos.
        self.proceso = factories.crear_proceso().name
        self.d1 = factories.crear_documento_controlado(
            proceso=self.proceso, tipo_documento="Procedimiento", titulo="Proc de prueba"
        )
        self.d2 = factories.crear_documento_controlado(
            proceso=self.proceso, tipo_documento="Manual", titulo="Manual de prueba"
        )

    def test_filas_incluye_los_documentos_del_proceso(self):
        """Cada Documento Controlado del proceso aparece como una fila."""
        filas = _filas_lista_maestra(proceso=self.proceso)
        codigos = {f[0] for f in filas}  # col 0 = Código (name)
        self.assertIn(self.d1.name, codigos)
        self.assertIn(self.d2.name, codigos)
        self.assertEqual(len(filas), 2)

    def test_ancho_de_fila_coincide_con_cabeceras(self):
        """Cada fila tiene tantas celdas como columnas declaradas."""
        filas = _filas_lista_maestra(proceso=self.proceso)
        self.assertTrue(filas)
        for f in filas:
            self.assertEqual(len(f), len(_CABECERAS))

    def test_filtro_por_estado(self):
        """El filtro por estado restringe las filas devueltas."""
        # Ambos arrancan en Borrador (estado inicial del control documental).
        filas_borrador = _filas_lista_maestra(estado="Borrador", proceso=self.proceso)
        self.assertEqual(len(filas_borrador), 2)
        filas_publicado = _filas_lista_maestra(estado="Publicado", proceso=self.proceso)
        self.assertEqual(len(filas_publicado), 0)

    def test_xlsx_es_binario_valido(self):
        """make_xlsx sobre [cabeceras + filas] produce un .xlsx (firma ZIP 'PK')."""
        filas = _filas_lista_maestra(proceso=self.proceso)
        xlsx = make_xlsx([_CABECERAS] + filas, "Lista Maestra")
        data = xlsx.getvalue()
        self.assertGreater(len(data), 0)
        self.assertEqual(data[:2], b"PK")
