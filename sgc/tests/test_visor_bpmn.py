# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""El BPMN se ve dentro del formulario, y verlo no permite cambiarlo.

Un `.bpmn` adjunto a un documento es XML: el navegador solo sabe ofrecerlo para
descargar. Por eso el diagrama se dibuja embebido en la propia ficha y en el propio
procedimiento, que es donde se consulta.

La parte delicada es que el visor reutiliza el bundle del **Modeler** (bpmn-js expone
`BpmnJS`, no el NavigatedViewer). Un modeler sin frenos permitiría arrastrar cajas en
una pantalla que se presenta como de consulta, y en un SGC eso es peor que no ver nada:
sugiere que el diagrama se editó cuando no se guardó. Estos tests fijan ese contrato.
"""
import pathlib
import re

import frappe
from frappe.tests.utils import FrappeTestCase

RAIZ = pathlib.Path(frappe.get_app_path("sgc"))
VISOR = RAIZ / "public" / "bpmn" / "visor.js"


class TestVisorBPMN(FrappeTestCase):
    def test_el_visor_esta_en_los_dos_doctypes_donde_se_consulta(self):
        for doctype in ("Procedimiento", "Ficha Caracterizacion Proceso"):
            campos = {f.fieldname: f for f in frappe.get_meta(doctype).fields}
            self.assertIn("visor_bpmn", campos, f"{doctype} no tiene el visor")
            self.assertEqual(campos["visor_bpmn"].fieldtype, "HTML")

    def test_el_visor_no_puede_guardar(self):
        """Solo el editor escribe. Si el visor llamara a guardar_bpmn, un clic
        accidental sobrescribiría el diagrama institucional."""
        fuente = VISOR.read_text(encoding="utf-8")
        self.assertNotIn("guardar_bpmn", fuente)
        self.assertNotIn("saveXML", fuente)

    def test_el_visor_cancela_la_edicion(self):
        """Los eventos de edición se cancelan con prioridad alta; sin esto, el
        modeler dejaría mover cajas en una pantalla de solo lectura."""
        fuente = VISOR.read_text(encoding="utf-8")
        for evento in ("shape.move.start", "connect.start", "create.start", "contextPad.open"):
            self.assertIn(evento, fuente, f"no se cancela {evento}")
        self.assertRegex(fuente, r"eventBus\.on\(evento,\s*\d{4,},\s*\(\)\s*=>\s*false\)")

    def test_el_encuadre_exige_un_lienzo_utilizable(self):
        """`fit-viewport` divide por el tamaño del contenedor. Comprobar solo que es
        mayor que cero no basta: un formulario a medio dibujar da un lienzo de 2 px de
        ancho, y con eso bpmn-js lanza «non-finite value on SVGMatrix». Medido en el
        banco de pruebas antes de fijar el mínimo."""
        fuente = VISOR.read_text(encoding="utf-8")
        self.assertIn("sgc.bpmn.MIN_LIENZO", fuente)
        self.assertRegex(fuente, r"offsetWidth >= min && nodo\.offsetHeight >= min")
        # y si no se puede encuadrar todavía, se reintenta en vez de rendirse
        self.assertRegex(fuente, r"restantes > 0[\s\S]{0,120}setTimeout")

    def test_el_visor_solo_usa_assets_propios(self):
        """El CSP de Frappe bloquea los CDN: todo lo que cargue el visor tiene que
        salir de /assets/sgc/."""
        fuente = VISOR.read_text(encoding="utf-8")
        for url in re.findall(r"[\"']((?:https?:)?//[^\"']+)[\"']", fuente):
            self.fail(f"el visor carga un recurso externo: {url}")

    def test_los_formularios_montan_el_visor_y_conservan_el_boton(self):
        pares = {
            "procedimiento": "Procedimiento",
            "ficha_caracterizacion_proceso": "Ficha Caracterizacion Proceso",
        }
        for carpeta, doctype in pares.items():
            js = (RAIZ / "sgc_procesos" / "doctype" / carpeta / f"{carpeta}.js").read_text(encoding="utf-8")
            self.assertIn('sgc.bpmn.montar(frm, "visor_bpmn")', js, f"{doctype} no monta el visor")
            self.assertIn("bpmn-editor", js, f"{doctype} perdió el acceso al editor")
