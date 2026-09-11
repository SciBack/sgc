# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""El documento controlado se lee sin descargarlo.

Lo pidió la DPGC el 10-sep-2026. Hasta entonces el adjunto solo ofrecía descarga,
y revisar 75 manuales bajándolos uno a uno no es revisar. El PDF se dibuja en la
propia ficha, que es donde se decide si pasa a revisión o se aprueba.
"""
import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

RAIZ = pathlib.Path(frappe.get_app_path("sgc"))
JS = RAIZ / "sgc_nucleo" / "doctype" / "documento_controlado" / "documento_controlado.js"


class TestVistaPreviaDocumento(FrappeTestCase):
    def test_el_campo_del_visor_existe_y_va_junto_al_adjunto(self):
        campos = {f.fieldname: f for f in frappe.get_meta("Documento Controlado").fields}
        self.assertIn("visor_documento", campos)
        self.assertEqual(campos["visor_documento"].fieldtype, "HTML")

        orden = [f.fieldname for f in frappe.get_meta("Documento Controlado").fields]
        self.assertEqual(
            orden.index("visor_documento"),
            orden.index("archivo") + 1,
            "la vista previa se lee junto al adjunto, no al final del formulario",
        )

    def test_el_visor_se_monta_y_sigue_al_adjunto(self):
        fuente = JS.read_text(encoding="utf-8")
        self.assertIn("sgc.documento.montar_visor", fuente)
        # si cambias el adjunto, la vista previa tiene que cambiar con él
        self.assertRegex(fuente, r"archivo\(frm\)\s*{")

    def test_solo_embebe_lo_que_el_navegador_dibuja(self):
        """Fingir una vista previa que no se ve sería peor que no ofrecerla."""
        fuente = JS.read_text(encoding="utf-8")
        self.assertIn("EXTENSIONES_EMBEBIBLES", fuente)
        self.assertIn("application/pdf", fuente)
        self.assertIn("Abrir en pestaña nueva", fuente)

    def test_la_url_del_adjunto_entra_escapada(self):
        """El nombre del fichero lo elige quien lo sube."""
        fuente = JS.read_text(encoding="utf-8")
        self.assertNotRegex(fuente, r'src="\$\{url\}')
        self.assertIn("frappe.utils.escape_html(url)", fuente)
