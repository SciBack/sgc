# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""El editor no puede estorbar a lo que se edita, y debe dejar entrar y salir el diagrama.

Dos cosas que se vieron usándolo en producción:

1. **La paleta tapaba el dibujo.** bpmn-js la monta flotando dentro del contenedor del
   canvas —`_getParentContainer()` devuelve el del canvas y no admite configuración— y no
   se puede arrastrar. Cae justo sobre la esquina superior izquierda, que es donde suele
   arrancar el flujo, y esa parte quedaba intocable. Sacar el nodo a una columna propia lo
   resolvía en apariencia y dejaba la paleta incómoda de usar: bpmn-js liga su interacción
   al contenedor del lienzo. Se deja donde bpmn-js la pone y se corre el diagrama al
   ajustar, que es como se comporta bpmn.io.

2. **No había vuelta desde un editor de escritorio.** Se podía descargar el `.bpmn` para
   abrirlo en Bizagi, pero no devolverlo: había que pasar por el panel de adjuntos, que
   nadie encuentra. Ahora se importa desde el propio editor.

3. **No había forma de arrepentirse.** Con el diagrama a medio cambiar, la única salida
   era abandonar la página y confiar en que nada se hubiera escrito. Ahora hay «Descartar
   cambios», que vuelve al último guardado previa confirmación.

Importar NO guarda: carga el diagrama en pantalla y avisa de que hay que pulsar «Guardar».
Que un fichero de fuera se persista sin un acto explícito sería justo lo que un SGC no
puede permitirse.
"""
import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

RAIZ = pathlib.Path(frappe.get_app_path("sgc"))
EDITOR = RAIZ / "sgc_nucleo" / "page" / "bpmn_editor" / "bpmn_editor.js"


class TestEditorBPMN(FrappeTestCase):
    def setUp(self):
        self.fuente = EDITOR.read_text(encoding="utf-8")

    def test_la_paleta_se_queda_donde_bpmn_js_la_pone(self):
        self.assertNotIn("desacoplar_paleta", self.fuente, "mover el nodo de la paleta la vuelve incomoda")
        self.assertNotIn("bpmn-palette-host", self.fuente, "la paleta no vive en una columna aparte")

    def test_el_ajuste_deja_libre_la_franja_que_ocupa_la_paleta(self):
        bloque = self.fuente[self.fuente.index("\tfit()") : self.fuente.index("\tsave()")]
        self.assertIn("MARGEN_PALETA", bloque, "el ajuste reserva el ancho de la paleta")
        self.assertIn("canvas.viewbox(", bloque, "se corre el diagrama, no se toca el DOM")

    def test_se_puede_importar_un_bpmn_editado_fuera(self):
        self.assertIn("importar()", self.fuente, "falta la importación")
        self.assertIn("bpmn-importar", self.fuente, "la importación debe tener su botón visible")
        self.assertIn("importXML", self.fuente)

    def test_importar_no_guarda_por_su_cuenta(self):
        bloque = self.fuente[self.fuente.index("\timportar()") : self.fuente.index("\tfit()")]
        self.assertNotIn("guardar_bpmn", bloque, "importar nunca debe persistir por su cuenta")
        self.assertNotIn("this.save()", bloque, "importar nunca debe llamar a guardar")
        self.assertIn("Guardar", bloque, "debe avisar de que hay que guardar")

    def test_se_pueden_descartar_los_cambios(self):
        self.assertIn("descartar()", self.fuente, "falta la acción de descartar")
        self.assertIn("bpmn-descartar", self.fuente, "descartar debe tener su botón visible")

    def test_descartar_pide_confirmacion_y_recarga_lo_guardado(self):
        bloque = self.fuente[self.fuente.index("\tdescartar()") : self.fuente.index("\tmarcar_sucio(")]
        self.assertIn("frappe.confirm", bloque, "descartar no puede ser irreversible sin preguntar")
        self.assertIn("this.open(this.current.file_url)", bloque, "descartar recarga el adjunto guardado")
        self.assertNotIn("guardar_bpmn", bloque, "descartar nunca escribe")

    def test_el_editor_sabe_si_hay_cambios_sin_guardar(self):
        self.assertIn("commandStack.changed", self.fuente, "hay que escuchar los cambios del lienzo")
        self.assertIn("marcar_sucio(false)", self.fuente, "el flag se limpia al abrir y al guardar")
        self.assertEqual(
            self.fuente.count("this.marcar_sucio(false)"),
            2,
            "el flag se limpia exactamente en dos sitios: al cargar y al guardar",
        )

    def test_descargar_sigue_disponible_para_el_viaje_de_ida(self):
        self.assertIn("Descargar .bpmn", self.fuente)
        self.assertIn("saveXML", self.fuente)

    def test_el_boton_del_formulario_no_cambia_de_nombre(self):
        proc = (RAIZ / "sgc_procesos" / "doctype" / "procedimiento" / "procedimiento.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('__("Editar BPMN")', proc, "el botón que abre el editor es «Editar BPMN»")
