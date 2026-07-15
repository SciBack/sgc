# Copyright (c) 2026, SciBack and Contributors
# See license.txt
"""Tests de integracion del modulo M03 — Control documental (Documento Controlado).

Cubren la logica de negocio real del controlador
(`sgc/sgc_nucleo/doctype/documento_controlado/documento_controlado.py`):

- Codigo SGC auto `[PROCESO]-[SIGLA]-[NNN]` con correlativo = max sufijo + 1,
  robusto a borrados intermedios; sigla por tipo documental; version por defecto.
- Workflow de 6 estados: transiciones validas e invalidas.
- Requisitos por estado (archivo / revisado_por / aprobado_por).
- Descripcion de cambio obligatoria al versionar.
- Al publicar: fija fecha_publicacion + fecha_proxima_revision anual, archiva el
  cambio en el historial y obsoleta el documento reemplazado.

Cada test corre en su propia transaccion con rollback automatico
(frappe.tests.IntegrationTestCase). Las factories no limpian.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_years

from sgc.tests import factories

# Un valor de Attach cualquiera sirve como "archivo presente": el controlador solo
# comprueba que el campo tenga contenido, no que el fichero exista fisicamente.
ARCHIVO = "/files/documento-prueba.pdf"
# Usuario siempre existente en un site Frappe, valido para los Link a User.
USER = "Administrator"


class IntegrationTestDocumentoControlado(IntegrationTestCase):
    def setUp(self):
        # Un proceso propio por test para aislar el correlativo de codigos.
        self.proceso = factories.crear_proceso().name

    # ------------------------------------------------------------------ helpers
    def _crear(self, tipo="Procedimiento", **overrides):
        return factories.crear_documento_controlado(
            proceso=self.proceso, tipo_documento=tipo, **overrides
        )

    def _sufijo(self, name):
        """Ultimos 3 caracteres del codigo (el correlativo NNN)."""
        return name.rsplit("-", 1)[-1]

    # ---------------------------------------------------------- codigo / defaults
    def test_codigo_correlativo_incremental(self):
        """3 docs del mismo proceso+tipo -> correlativos 001, 002, 003."""
        d1 = self._crear()
        d2 = self._crear()
        d3 = self._crear()
        self.assertEqual(self._sufijo(d1.name), "001")
        self.assertEqual(self._sufijo(d2.name), "002")
        self.assertEqual(self._sufijo(d3.name), "003")
        # El prefijo es el proceso en mayusculas y la sigla del tipo (PR).
        self.assertTrue(d1.name.endswith("-PR-001"))
        self.assertTrue(d1.name.startswith(self.proceso.upper().replace(" ", "")[:12]))

    def test_correlativo_robusto_a_borrados(self):
        """Borrar un documento intermedio NO hace reusar su numero (max+1, no count)."""
        d1 = self._crear()
        d2 = self._crear()
        d3 = self._crear()
        self.assertEqual(self._sufijo(d3.name), "003")

        # Se borra el del medio (002): quedan 001 y 003.
        frappe.delete_doc("Documento Controlado", d2.name, force=True, ignore_permissions=True)

        d4 = self._crear()
        # Con count() daria 003 (colision); con max+1 da 004.
        self.assertEqual(self._sufijo(d4.name), "004")

    def test_correlativo_separado_por_tipo(self):
        """El correlativo se cuenta por (proceso, tipo): cada tipo arranca en 001."""
        proc = self._crear(tipo="Procedimiento")
        manual = self._crear(tipo="Manual")
        self.assertTrue(proc.name.endswith("-PR-001"))
        self.assertTrue(manual.name.endswith("-MN-001"))

    def test_sigla_por_tipo_documental(self):
        """La sigla del codigo depende del tipo documental (Manual -> MN)."""
        d = self._crear(tipo="Manual")
        self.assertIn("-MN-", d.name)

    def test_version_por_defecto_1_0(self):
        """Si no se indica version, before_insert la fija en 1.0."""
        d = self._crear()
        self.assertEqual(d.version, "1.0")

    # -------------------------------------------------------------- transiciones
    def test_flujo_completo_borrador_a_publicado(self):
        """Camino feliz del workflow completo + efectos de la publicacion."""
        d = self._crear(archivo=ARCHIVO)
        self.assertEqual(d.estado, "Borrador")

        d.estado = "En revision"
        d.save(ignore_permissions=True)

        d.estado = "Aprobado"
        d.revisado_por = USER
        d.save(ignore_permissions=True)

        d.estado = "Publicado"
        d.aprobado_por = USER
        d.save(ignore_permissions=True)

        d.reload()
        self.assertEqual(d.estado, "Publicado")
        # Al publicar se fija fecha_publicacion y la proxima revision a un anio.
        self.assertTrue(d.fecha_publicacion)
        self.assertEqual(
            str(d.fecha_proxima_revision), str(add_years(d.fecha_publicacion, 1))
        )

    def test_transicion_valida_observado_vuelve_a_borrador(self):
        """Observado permite regresar a Borrador (ciclo de correccion)."""
        d = self._crear(archivo=ARCHIVO)
        d.estado = "En revision"
        d.save(ignore_permissions=True)
        d.estado = "Observado"
        d.save(ignore_permissions=True)
        # Observado -> Borrador es una transicion permitida.
        d.estado = "Borrador"
        d.save(ignore_permissions=True)
        self.assertEqual(frappe.db.get_value("Documento Controlado", d.name, "estado"), "Borrador")

    def test_transicion_invalida_lanza_error(self):
        """Borrador -> Obsoleto no esta permitido (Borrador solo va a En revision)."""
        d = self._crear(archivo=ARCHIVO)
        d.estado = "Obsoleto"
        with self.assertRaises(frappe.ValidationError):
            d.save(ignore_permissions=True)

    def test_publicado_es_terminal_salvo_obsoleto(self):
        """Desde Publicado solo se puede ir a Obsoleto; regresar a Borrador falla."""
        d = self._crear(archivo=ARCHIVO, aprobado_por=USER, revisado_por=USER)
        d.estado = "En revision"
        d.save(ignore_permissions=True)
        d.estado = "Aprobado"
        d.save(ignore_permissions=True)
        d.estado = "Publicado"
        d.save(ignore_permissions=True)

        d.estado = "Borrador"
        with self.assertRaises(frappe.ValidationError):
            d.save(ignore_permissions=True)

    # ---------------------------------------------------- requisitos por estado
    def test_en_revision_exige_archivo(self):
        """No se puede enviar a revision sin adjuntar el archivo."""
        d = self._crear()  # sin archivo
        d.estado = "En revision"
        with self.assertRaises(frappe.ValidationError):
            d.save(ignore_permissions=True)

    def test_aprobado_exige_revisado_por(self):
        """No se puede aprobar sin indicar quien reviso."""
        d = self._crear(archivo=ARCHIVO)
        d.estado = "En revision"
        d.save(ignore_permissions=True)
        d.estado = "Aprobado"  # sin revisado_por
        with self.assertRaises(frappe.ValidationError):
            d.save(ignore_permissions=True)

    def test_publicar_exige_aprobado_por(self):
        """No se puede publicar sin quien lo aprobo (aun teniendo archivo)."""
        d = self._crear(archivo=ARCHIVO, revisado_por=USER)
        d.estado = "En revision"
        d.save(ignore_permissions=True)
        d.estado = "Aprobado"
        d.save(ignore_permissions=True)
        d.estado = "Publicado"  # sin aprobado_por
        with self.assertRaises(frappe.ValidationError):
            d.save(ignore_permissions=True)

    # ----------------------------------------------------- descripcion de cambio
    def test_versionar_sin_descripcion_falla(self):
        """Cambiar de version sin describir el cambio esta prohibido."""
        d = self._crear()
        d.version = "2.0"  # sin descripcion_cambio
        with self.assertRaises(frappe.ValidationError):
            d.save(ignore_permissions=True)

    def test_versionar_con_descripcion_ok(self):
        """Con descripcion del cambio, el versionado se guarda sin error."""
        d = self._crear()
        d.version = "2.0"
        d.descripcion_cambio = "Se actualizo el alcance del procedimiento."
        d.save(ignore_permissions=True)
        self.assertEqual(frappe.db.get_value("Documento Controlado", d.name, "version"), "2.0")

    # ------------------------------------------------ publicacion: efectos cruzados
    def test_al_publicar_archiva_el_cambio_en_historial(self):
        """Al publicar, la descripcion del cambio pasa al historial y se limpia."""
        d = self._crear(archivo=ARCHIVO, aprobado_por=USER, revisado_por=USER)
        d.version = "2.0"
        d.descripcion_cambio = "Version publicada tras revision anual."
        d.save(ignore_permissions=True)  # versionado valido

        d.estado = "En revision"
        d.save(ignore_permissions=True)
        d.estado = "Aprobado"
        d.save(ignore_permissions=True)
        d.estado = "Publicado"
        d.save(ignore_permissions=True)

        d.reload()
        # La descripcion se congela en el historial y el campo suelto queda vacio.
        self.assertFalse(d.descripcion_cambio)
        versiones = [fila.version for fila in d.historial_cambios]
        self.assertIn("2.0", versiones)

    def test_al_publicar_obsoleta_el_reemplazado(self):
        """Publicar un documento que reemplaza a otro deja al anterior en Obsoleto."""
        # Documento vigente (publicado directamente: en alta no hay chequeo de transicion).
        anterior = self._crear(archivo=ARCHIVO, aprobado_por=USER, estado="Publicado")
        self.assertEqual(
            frappe.db.get_value("Documento Controlado", anterior.name, "estado"), "Publicado"
        )

        # Nuevo documento que lo reemplaza, tambien publicado en el alta.
        nuevo = self._crear(
            archivo=ARCHIVO, aprobado_por=USER, estado="Publicado", reemplaza_a=anterior.name
        )
        self.assertEqual(nuevo.estado, "Publicado")
        # El reemplazado quedo marcado Obsoleto por el efecto cruzado de la publicacion.
        self.assertEqual(
            frappe.db.get_value("Documento Controlado", anterior.name, "estado"), "Obsoleto"
        )
