# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""La exportación a BPMN produce diagramas coherentes, no solo válidos.

Un `.bpmn` puede estar bien formado, validar contra el esquema de la OMG y aun
así describir un proceso imposible: una tarea a la que no llega nada, dos flechas
idénticas entre los mismos nodos, una referencia a un elemento que no existe.
Nada de eso lo detecta un validador de esquema, y a simple vista tampoco: hay que
seguir las flechas una por una.

Estos tests recorren el grafo de los 14 workflows y comprueban justo eso.

Lo que NO se considera un error, aunque lo parezca:

  - **Dos tareas con el mismo nombre.** En el modelo por acciones, "Observar"
    desde "En revisión" y "Observar" desde "Aprobado" son dos actividades reales
    en momentos distintos del proceso.
  - **Dos tareas con el mismo nombre en carriles distintos.** Es el patrón de
    doble rol: `Evidencia` permite "Subsanar" al Responsable de Programa y al
    Dueño de Proceso. Que se vean separadas es la gracia.
"""
import xml.etree.ElementTree as ET
from collections import Counter

import frappe
from frappe.tests import IntegrationTestCase

from sgc import bpmn

M = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
TIPOS_NODO = ("userTask", "serviceTask", "sendTask", "startEvent", "endEvent",
              "exclusiveGateway", "parallelGateway")


def _grafo(xml):
    """Nodos, flujos y carriles de un BPMN, con un parser XML real.

    Con expresiones regulares esto se hace mal: el orden de los atributos no está
    garantizado y una regex que espere `sourceRef` justo tras `id` se salta todos
    los flujos que llevan nombre, que son la mayoría.
    """
    proceso = ET.fromstring(xml).find(f"{M}process")
    nodos = {e.get("id"): t for t in TIPOS_NODO for e in proceso.iter(f"{M}{t}")}
    flujos = [(e.get("id"), e.get("sourceRef"), e.get("targetRef"))
              for e in proceso.iter(f"{M}sequenceFlow")]
    carril_de = {}
    for lane in proceso.iter(f"{M}lane"):
        for ref in lane.iter(f"{M}flowNodeRef"):
            carril_de[ref.text] = lane.get("name")
    return nodos, flujos, carril_de


class IntegrationTestBpmn(IntegrationTestCase):
    """Coherencia de los diagramas exportados."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.specs = bpmn.specs_de_workflows()
        cls.diagramas = {s["document_type"]: bpmn.construir(s) for _m, s in cls.specs}

    def test_se_exportan_todos_los_workflows_declarados(self):
        """Si alguien añade un workflow y no aparece aquí, este test lo canta.

        El descubrimiento es automático justo para esto: una lista escrita a mano
        se queda corta en silencio, que es como trece workflows estuvieron sin
        documentar.
        """
        self.assertGreaterEqual(len(self.specs), 14)
        for _modulo, spec in self.specs:
            self.assertIn(spec["document_type"], self.diagramas)

    def test_ningun_flujo_vuelve_sobre_si_mismo(self):
        for dt, xml in self.diagramas.items():
            _nodos, flujos, _c = _grafo(xml)
            bucles = [f[0] for f in flujos if f[1] == f[2]]
            self.assertFalse(bucles, f"«{dt}» tiene flujos que salen y entran al mismo nodo: {bucles}")

    def test_no_hay_flechas_duplicadas_entre_los_mismos_nodos(self):
        """Dos flechas idénticas se dibujan una encima de otra y ocultan dato."""
        for dt, xml in self.diagramas.items():
            _nodos, flujos, _c = _grafo(xml)
            repetidos = [par for par, n in Counter((f[1], f[2]) for f in flujos).items() if n > 1]
            self.assertFalse(repetidos, f"«{dt}» tiene flechas duplicadas: {repetidos}")

    def test_todas_las_referencias_apuntan_a_un_nodo_existente(self):
        for dt, xml in self.diagramas.items():
            nodos, flujos, _c = _grafo(xml)
            rotas = [f[0] for f in flujos if f[1] not in nodos or f[2] not in nodos]
            self.assertFalse(rotas, f"«{dt}» tiene referencias a nodos inexistentes: {rotas}")

    def test_todo_nodo_es_alcanzable_y_lleva_a_alguna_parte(self):
        """Una tarea sin entrada no ocurre nunca; sin salida, deja el proceso colgado."""
        for dt, xml in self.diagramas.items():
            nodos, flujos, _c = _grafo(xml)
            entran = {f[2] for f in flujos}
            salen = {f[1] for f in flujos}
            sin_entrada = [n for n, t in nodos.items() if t != "startEvent" and n not in entran]
            sin_salida = [n for n, t in nodos.items() if t != "endEvent" and n not in salen]
            self.assertFalse(sin_entrada, f"«{dt}»: nodos a los que no llega nada: {sin_entrada}")
            self.assertFalse(sin_salida, f"«{dt}»: nodos que no llevan a nada: {sin_salida}")

    def test_cada_nodo_esta_en_un_carril(self):
        """Un nodo fuera de todo carril no dice quién lo ejecuta."""
        for dt, xml in self.diagramas.items():
            nodos, _f, carril_de = _grafo(xml)
            huerfanos = [n for n in nodos if n not in carril_de]
            self.assertFalse(huerfanos, f"«{dt}» tiene nodos fuera de carril: {huerfanos}")

    def test_las_tareas_son_acciones_y_los_rombos_estados(self):
        """El modelo: la tarea es lo que alguien hace; el rombo, donde se decide.

        Se comprueba contra la definición del workflow: cada nombre de tarea debe
        ser una acción declarada, y cada rombo un estado con más de una salida.
        """
        for _modulo, spec in self.specs:
            xml = self.diagramas[spec["document_type"]]
            proceso = ET.fromstring(xml).find(f"{M}process")
            acciones = {t[1] for t in spec["transitions"]}
            for tarea in proceso.iter(f"{M}userTask"):
                self.assertIn(tarea.get("name"), acciones,
                              f"«{spec['document_type']}»: la tarea «{tarea.get('name')}» "
                              "no es ninguna acción del workflow")
            salidas = Counter(t[0] for t in spec["transitions"])
            for rombo in proceso.iter(f"{M}exclusiveGateway"):
                self.assertGreater(salidas[rombo.get("name")], 1,
                                   f"«{spec['document_type']}»: el rombo «{rombo.get('name')}» "
                                   "no corresponde a un estado con varias salidas")

    def test_el_carril_es_el_rol_autorizado_a_ejecutar(self):
        """Quien aparece en el carril debe poder ejecutar esa transición.

        Es lo que hace legible la segregación de funciones: si el carril fuera
        quien puede editar el documento, el diagrama diría quién lo toca, no
        quién puede moverlo de estado, que es el control que importa.
        """
        for _modulo, spec in self.specs:
            xml = self.diagramas[spec["document_type"]]
            _nodos, _flujos, carril_de = _grafo(xml)
            proceso = ET.fromstring(xml).find(f"{M}process")
            por_accion = {}
            for t in spec["transitions"]:
                por_accion.setdefault(t[1], set()).add(t[3])
            for tarea in proceso.iter(f"{M}userTask"):
                esperados = por_accion[tarea.get("name")]
                self.assertIn(carril_de.get(tarea.get("id")), esperados,
                              f"«{spec['document_type']}»: «{tarea.get('name')}» está en un "
                              "carril que no puede ejecutarla")

    def test_los_identificadores_son_ascii_y_unicos(self):
        """Un id con eñe o tilde valida contra el XSD pero bpmn-js lo descarta."""
        for dt, xml in self.diagramas.items():
            ids = [e.get("id") for e in ET.fromstring(xml).iter() if e.get("id")]
            no_ascii = [i for i in ids if not i.isascii()]
            self.assertFalse(no_ascii, f"«{dt}» tiene identificadores no ASCII: {no_ascii}")
            repetidos = [i for i, n in Counter(ids).items() if n > 1]
            self.assertFalse(repetidos, f"«{dt}» tiene identificadores repetidos: {repetidos}")

    def test_los_metadatos_del_sgc_viajan_en_cada_transicion(self):
        """El rol y la autoaprobación son lo que un auditor viene a mirar."""
        for _modulo, spec in self.specs:
            xml = self.diagramas[spec["document_type"]]
            self.assertEqual(xml.count("<sgc:transicion"), len(spec["transitions"]),
                             f"«{spec['document_type']}»: faltan metadatos de transición")

    def test_el_diagrama_trae_posiciones(self):
        """Sin la sección de dibujo, un modelador abre el fichero y no pinta nada."""
        for dt, xml in self.diagramas.items():
            self.assertIn("BPMNDiagram", xml, f"«{dt}» no trae sección de diagrama")
            self.assertIn("dc:Bounds", xml, f"«{dt}» no trae coordenadas")

    def test_conserva_las_posiciones_ajustadas_a_mano(self):
        """Regenerar no puede destruir el trabajo de quien recolocó el diagrama.

        Se preservan las posiciones de los NODOS (tareas, rombos, eventos). El
        contenedor y los carriles se recalculan a propósito: su tamaño depende de
        dónde acaben los nodos, así que fijarlos dejaría cajas fuera del marco.
        """
        _modulo, spec = self.specs[0]
        posiciones = bpmn.layout_de(bpmn.construir(spec))
        tarea = next(k for k in posiciones if k.startswith("Task_"))
        x, y, w, h = posiciones[tarea]
        movido = dict(posiciones)
        movido[tarea] = (x + 500, y + 40, w, h)

        regenerado = bpmn.layout_de(bpmn.construir(spec, layout_previo=movido))

        self.assertEqual(regenerado[tarea], (x + 500, y + 40, w, h))

    def test_frappe_esta_disponible(self):
        """Guarda de contexto: estos tests corren dentro del sitio, no sueltos."""
        self.assertTrue(frappe.db)
