# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Copias controladas y documentación externa (#36).

  Documentación externa
    - se envía a revisión con el enlace y sin archivo; los demás tipos no
    - el enlace solo acepta http(s); la sigla del código es DE
  Solo consulta
    - exige un archivo privado que se pueda ver en pantalla
    - quien solo lee no lo obtiene por NINGUNA de las cuatro puertas:
      URL directa / download_file, zip_files y el adjunto del correo
    - quien puede editarlo, sí
  Registro
    - el visor deja una Consulta y la descarga una Descarga en Access Log
    - el informe los une con las descargas por enlace directo

Todo se deshace al final de cada test (rollback de `IntegrationTestCase`).
"""

import io
import zipfile

import frappe
from frappe.core.doctype.file.utils import find_file_by_url
from frappe.tests import IntegrationTestCase

from sgc import documentos
from sgc.sgc_nucleo.report.accesos_a_documentos import accesos_a_documentos as informe
from sgc.tests import factories

LECTOR = "sgc-prueba-copias-lector@example.com"
EDITOR = "sgc-prueba-copias-editor@example.com"
ROL_LECTURA = "Decano/Director (lectura)"
ROL_EDICION = "Dueño de Proceso"
REGLA_PUBLICACION = "SGC - Documento Controlado publicado"


def _pdf():
    """Un PDF de verdad: Frappe valida los PDF al subirlos (pypdf)."""
    from pypdf import PdfWriter

    escritor = PdfWriter()
    escritor.add_blank_page(width=72, height=72)
    salida = io.BytesIO()
    escritor.write(salida)
    return salida.getvalue()


PDF = _pdf()


def _usuario(correo, rol):
    if not frappe.db.exists("User", correo):
        u = frappe.get_doc({"doctype": "User", "email": correo, "first_name": correo.split("@")[0],
                            "send_welcome_email": 0})
        u.append("roles", {"role": rol})
        u.insert(ignore_permissions=True)


class IntegrationTestCopiasControladas(IntegrationTestCase):
    def setUp(self):
        factories.desactivar_workflow("Documento Controlado")
        _usuario(LECTOR, ROL_LECTURA)
        _usuario(EDITOR, ROL_EDICION)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()

    # -- helpers -----------------------------------------------------------
    def _documento(self, solo_consulta=0, nombre_fichero="manual.pdf", privado=1, **overrides):
        doc = factories.crear_documento_controlado(**overrides)
        fichero = frappe.get_doc(
            {
                "doctype": "File",
                "file_name": nombre_fichero,
                "content": PDF,
                "is_private": privado,
                "attached_to_doctype": documentos.DOCTYPE,
                "attached_to_name": doc.name,
                "attached_to_field": "archivo",
            }
        ).insert(ignore_permissions=True)
        doc.reload()
        doc.archivo = fichero.file_url
        doc.solo_consulta = solo_consulta
        doc.save(ignore_permissions=True)
        return doc, fichero

    def _como(self, usuario):
        frappe.set_user(usuario)
        self.addCleanup(frappe.set_user, "Administrator")

    def _accesos(self, doc, metodo):
        return frappe.get_all(
            "Access Log",
            filters={"export_from": documentos.DOCTYPE, "reference_document": doc.name, "method": metodo},
            fields=["user"],
        )

    # ======================================================================
    # Documentación externa
    # ======================================================================
    def test_un_documento_externo_va_a_revision_con_el_enlace_y_sin_archivo(self):
        doc = factories.crear_documento_controlado(
            tipo_documento=documentos.EXTERNA, url_externa="https://normas.example.org/iso-9001"
        )
        self.assertIn("-DE-", doc.name)
        doc.estado = "En revision"
        doc.save(ignore_permissions=True)
        self.assertEqual(doc.estado, "En revision")

    def test_otro_tipo_con_solo_un_enlace_no_va_a_revision(self):
        doc = factories.crear_documento_controlado(url_externa="https://normas.example.org/x")
        doc.estado = "En revision"
        with self.assertRaises(frappe.ValidationError):
            doc.save(ignore_permissions=True)

    def test_el_enlace_externo_solo_acepta_http(self):
        with self.assertRaises(frappe.ValidationError):
            factories.crear_documento_controlado(
                tipo_documento=documentos.EXTERNA, url_externa="javascript:alert(1)"
            )

    # ======================================================================
    # Solo consulta: lo que exige
    # ======================================================================
    def test_solo_consulta_sin_archivo_falla(self):
        with self.assertRaises(frappe.ValidationError):
            factories.crear_documento_controlado(solo_consulta=1)

    def test_solo_consulta_con_un_formato_que_no_se_ve_en_pantalla_falla(self):
        with self.assertRaises(frappe.ValidationError):
            self._documento(solo_consulta=1, nombre_fichero="manual.docx")

    def test_solo_consulta_con_un_archivo_publico_falla(self):
        """Un fichero público lo sirve el servidor web sin pasar por Frappe."""
        with self.assertRaises(frappe.ValidationError):
            self._documento(solo_consulta=1, privado=0)

    # ======================================================================
    # Solo consulta: quién descarga
    # ======================================================================
    def test_quien_solo_lee_no_descarga_y_quien_edita_si(self):
        doc, _ = self._documento(solo_consulta=1)
        self.assertFalse(documentos.puede_descargar(doc, LECTOR))
        self.assertTrue(documentos.puede_descargar(doc, EDITOR))

    def test_sin_solo_consulta_quien_lee_descarga(self):
        doc, _ = self._documento()
        self.assertTrue(documentos.puede_descargar(doc, LECTOR))

    # -- puertas 1 y 2: URL directa y download_file -------------------------
    def test_la_url_directa_no_se_entrega_a_quien_solo_lee(self):
        _, fichero = self._documento(solo_consulta=1)
        self._como(LECTOR)
        self.assertIsNone(find_file_by_url(fichero.file_url))

    def test_la_url_directa_si_se_entrega_a_quien_edita(self):
        _, fichero = self._documento(solo_consulta=1)
        self._como(EDITOR)
        self.assertIsNotNone(find_file_by_url(fichero.file_url))

    def test_sin_solo_consulta_la_url_directa_sigue_como_antes(self):
        _, fichero = self._documento()
        self._como(LECTOR)
        self.assertIsNotNone(find_file_by_url(fichero.file_url))

    # -- puerta 3: zip_files ----------------------------------------------------
    def test_zip_files_deja_fuera_lo_que_no_se_puede_descargar(self):
        _, fichero = self._documento(solo_consulta=1)
        self._como(LECTOR)
        from frappe.core.doctype.file.file import File

        # La puerta existía: el zip de Frappe lo entrega a quien solo lee.
        self.assertEqual(len(zipfile.ZipFile(io.BytesIO(File.zip_files([fichero.name]))).namelist()), 1)

        documentos.zip_files(frappe.as_json([fichero.name]))
        contenido = zipfile.ZipFile(io.BytesIO(frappe.response["filecontent"]))
        self.assertEqual(contenido.namelist(), [])

    def test_zip_files_es_el_que_responde_por_la_api(self):
        self.assertEqual(
            frappe.override_whitelisted_method("frappe.core.api.file.zip_files"), "sgc.documentos.zip_files"
        )

    # -- puerta 4: el adjunto del correo de publicación ------------------------
    def _adjuntos_de_publicacion(self, doc):
        regla = frappe.get_doc("Notification", REGLA_PUBLICACION)
        return [a.get("file_url") for a in regla.get_attachment(doc) if "file_url" in a]

    def test_el_correo_de_publicacion_no_adjunta_un_documento_de_solo_consulta(self):
        doc, _ = self._documento(solo_consulta=1)
        self.assertEqual(self._adjuntos_de_publicacion(doc), [])

    def test_el_correo_de_publicacion_adjunta_los_demas(self):
        doc, fichero = self._documento()
        self.assertEqual(self._adjuntos_de_publicacion(doc), [fichero.file_url])

    def test_un_documento_externo_sin_archivo_no_lleva_adjunto_vacio(self):
        doc = factories.crear_documento_controlado(
            tipo_documento=documentos.EXTERNA, url_externa="https://normas.example.org/iso-9001"
        )
        self.assertEqual(self._adjuntos_de_publicacion(doc), [])

    # ======================================================================
    # El visor, la descarga y el registro
    # ======================================================================
    def test_quien_solo_lee_ve_el_documento_en_pantalla_y_queda_registrado(self):
        doc, _ = self._documento(solo_consulta=1)
        self._como(LECTOR)
        documentos.ver(doc.name)
        self.assertEqual(frappe.response["filecontent"], PDF)
        self.assertEqual(frappe.response["display_content_as"], "inline")
        self.assertEqual([r.user for r in self._accesos(doc, documentos.CONSULTA)], [LECTOR])

    def test_quien_solo_lee_no_descarga_desde_la_ficha(self):
        doc, _ = self._documento(solo_consulta=1)
        self._como(LECTOR)
        with self.assertRaises(frappe.PermissionError):
            documentos.descargar(doc.name)
        self.assertEqual(self._accesos(doc, documentos.DESCARGA), [])

    def test_quien_edita_descarga_y_queda_registrado(self):
        doc, _ = self._documento(solo_consulta=1)
        self._como(EDITOR)
        documentos.descargar(doc.name)
        self.assertEqual(frappe.response["display_content_as"], "attachment")
        self.assertEqual([r.user for r in self._accesos(doc, documentos.DESCARGA)], [EDITOR])

    def test_el_formulario_sabe_si_puede_descargar(self):
        doc, _ = self._documento(solo_consulta=1)
        self._como(LECTOR)
        visto = frappe.get_doc(documentos.DOCTYPE, doc.name)
        visto.run_method("onload")
        self.assertFalse(visto.get_onload().puede_descargar)

    def test_el_informe_une_consultas_descargas_y_enlaces_directos(self):
        from frappe.core.doctype.access_log.access_log import make_access_log

        doc, fichero = self._documento(solo_consulta=1)
        self._como(LECTOR)
        documentos.ver(doc.name)
        self._como(EDITOR)
        documentos.descargar(doc.name)
        make_access_log(doctype="File", document=fichero.name, file_type="pdf")
        frappe.set_user("Administrator")

        _, filas = informe.execute({"documento": doc.name})
        vistos = sorted((f["usuario"], f["acceso"]) for f in filas)
        self.assertEqual(
            vistos,
            sorted([(LECTOR, "Consulta"), (EDITOR, "Descarga"), (EDITOR, informe.FICHERO)]),
        )
        self.assertTrue(all(f["titulo"] == doc.titulo for f in filas))
