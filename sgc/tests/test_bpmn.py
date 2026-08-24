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
DI = "{http://www.omg.org/spec/BPMN/20100524/DI}"
DC = "{http://www.omg.org/spec/DD/20100524/DC}"
TIPOS_NODO = ("userTask", "serviceTask", "sendTask", "startEvent", "endEvent",
              "exclusiveGateway", "parallelGateway",
              # los eventos intermedios llevan las transiciones automáticas: sin
              # ellos aquí, sus flujos parecen apuntar a nodos inexistentes
              "intermediateCatchEvent", "intermediateThrowEvent")


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

    def test_un_final_no_tiene_salidas_ni_un_inicio_entradas(self):
        """La regla simétrica de la anterior, y la que faltaba.

        El test de arriba excluye los `endEvent` al buscar nodos sin salida —es
        correcto: un final no lleva a ninguna parte—, pero nunca comprobaba lo
        contrario. Así pasó desapercibido que el vencimiento de una evidencia
        salía DEL final «Valida»: BPMN 2.0 lo prohíbe y ninguna herramienta lo
        abre bien, y aun así el diagrama parecía sano en todo lo demás.
        """
        for dt, xml in self.diagramas.items():
            nodos, flujos, _c = _grafo(xml)
            finales = {n for n, t in nodos.items() if t == "endEvent"}
            inicios = {n for n, t in nodos.items() if t == "startEvent"}
            salen_de_un_fin = [f[0] for f in flujos if f[1] in finales]
            entran_a_un_inicio = [f[0] for f in flujos if f[2] in inicios]
            self.assertFalse(salen_de_un_fin,
                             f"«{dt}»: hay flujos que salen de un evento de fin: {salen_de_un_fin}")
            self.assertFalse(entran_a_un_inicio,
                             f"«{dt}»: hay flujos que entran a un evento de inicio: {entran_a_un_inicio}")

    def test_un_estado_final_que_caduca_solo_se_dibuja_con_rombo(self):
        """Quedarse en el estado también es un desenlace, y tiene que verse.

        Si un estado sin salidas humanas tiene además una transición automática,
        el documento puede acabar de dos maneras: quedarse ahí o que le ocurra lo
        automático. Dibujar solo el temporizador diría que toda evidencia válida
        acaba venciendo, que es falso.
        """
        for _modulo, spec in self.specs:
            dt = spec["document_type"]
            automaticas = bpmn.automaticas_de(dt)
            if not automaticas:
                continue
            salidas = {t[0] for t in spec["transitions"]}
            estados_finales = {e[0] for e in spec["states"]} - salidas
            desde_auto = {d for a in automaticas for d in a["desde"]}
            nodos, flujos, _c = _grafo(self.diagramas[dt])
            for estado in estados_finales & desde_auto:
                esperado = bpmn._id("Gateway", f"{estado}_espera")
                self.assertEqual(nodos.get(esperado), "exclusiveGateway",
                                 f"«{dt}»: «{estado}» caduca solo y no lleva rombo")
                salen = [f for f in flujos if f[1] == esperado]
                self.assertEqual(len(salen), 2,
                                 f"«{dt}»: el rombo de «{estado}» debe bifurcar en 2, no {len(salen)}")

    def test_regenerar_sin_cambios_deja_el_fichero_igual(self):
        """Generar dos veces tiene que dar lo mismo, byte a byte.

        Sin esto no se puede comprobar si un diagrama está al día: bastaba
        regenerar para que los 14 ficheros salieran distintos —el ancho del
        contenedor se releía como decimal y volvía a escribirse «1146.0» donde
        antes puso «1146»— y el ruido tapaba el cambio de verdad.
        """
        for _modulo, spec in self.specs:
            primera = bpmn.construir(spec)
            segunda = bpmn.construir(spec, layout_previo=bpmn.layout_de(primera))
            self.assertEqual(primera, segunda,
                             f"«{spec['document_type']}» cambia al regenerarlo sin tocar nada")

    def test_cada_nodo_esta_en_un_carril(self):
        """Un nodo fuera de todo carril no dice quién lo ejecuta."""
        for dt, xml in self.diagramas.items():
            nodos, _f, carril_de = _grafo(xml)
            huerfanos = [n for n in nodos if n not in carril_de]
            self.assertFalse(huerfanos, f"«{dt}» tiene nodos fuera de carril: {huerfanos}")

    def test_las_tareas_son_acciones_y_los_rombos_estados(self):
        """El modelo: la tarea es lo que alguien hace; el rombo, donde se decide.

        Se comprueba contra la definición del workflow: cada nombre de tarea debe
        ser una acción declarada, y cada rombo, un punto donde el proceso se
        bifurca de verdad. Hay dos maneras de bifurcarse, y las dos son legítimas:

          - **un estado con varias salidas** — alguien elige entre varias acciones;
          - **un estado final que además caduca solo** — nadie elige, pero el
            documento puede quedarse ahí o que le ocurra lo automático. Sin este
            segundo caso el temporizador tendría que colgar del evento de fin, y
            un fin no tiene salidas (lo prohíbe BPMN 2.0).
        """
        for _modulo, spec in self.specs:
            dt = spec["document_type"]
            xml = self.diagramas[dt]
            proceso = ET.fromstring(xml).find(f"{M}process")
            acciones = {t[1] for t in spec["transitions"]}
            for tarea in proceso.iter(f"{M}userTask"):
                self.assertIn(tarea.get("name"), acciones,
                              f"«{dt}»: la tarea «{tarea.get('name')}» "
                              "no es ninguna acción del workflow")
            salidas = Counter(t[0] for t in spec["transitions"])
            finales_que_caducan = ({e[0] for e in spec["states"]} - set(salidas)) & {
                d for a in bpmn.automaticas_de(dt) for d in a["desde"]}
            for rombo in proceso.iter(f"{M}exclusiveGateway"):
                estado = rombo.get("name")
                self.assertTrue(salidas[estado] > 1 or estado in finales_que_caducan,
                                f"«{dt}»: el rombo «{estado}» no corresponde ni a un estado "
                                "con varias salidas ni a uno que caduque solo")

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

        El desplazamiento de la prueba es horizontal y grande a propósito:
        horizontal para que la caja siga en su carril, y grande para que no
        aterrice encima de otra — las dos condiciones que se comprueban antes de
        aceptar el layout guardado.
        """
        _modulo, spec = self.specs[0]
        posiciones = bpmn.layout_de(bpmn.construir(spec))
        tarea = next(k for k in posiciones if k.startswith("Task_"))
        x, y, w, h = posiciones[tarea]
        movido = dict(posiciones)
        movido[tarea] = (x + 5000, y, w, h)

        regenerado = bpmn.layout_de(bpmn.construir(spec, layout_previo=movido))

        self.assertEqual(regenerado[tarea], (x + 5000, y, w, h))

    def test_un_ajuste_que_saca_la_caja_de_su_carril_se_descarta(self):
        """Y se descarta el layout ENTERO, no solo esa caja.

        En un diagrama de carriles la posición dice quién ejecuta la tarea, así
        que una caja en la banda del vecino afirma algo falso y la posición
        calculada tiene que ganar. Se descarta todo porque un diagrama mitad
        conservado mitad recalculado acaba con cajas superpuestas: las
        posiciones nuevas no saben qué celdas ocupan las viejas.
        """
        _modulo, spec = self.specs[0]
        posiciones = bpmn.layout_de(bpmn.construir(spec))
        tarea = next(k for k in posiciones if k.startswith("Task_"))
        x, y, w, h = posiciones[tarea]
        otra = next(k for k in posiciones if k.startswith("Task_") and k != tarea)
        ox, oy, ow, oh = posiciones[otra]
        fuera = dict(posiciones)
        fuera[tarea] = (x, y + 400, w, h)          # a la banda de otro carril
        fuera[otra] = (ox + 5000, oy, ow, oh)      # este sí sería válido

        regenerado = bpmn.layout_de(bpmn.construir(spec, layout_previo=fuera))

        self.assertEqual(regenerado[tarea], (x, y, w, h))
        self.assertEqual(regenerado[otra], (ox, oy, ow, oh),
                         "el ajuste válido del vecino también se descarta: es todo o nada")

    # ======================================================================
    # Transiciones automáticas: lo que el sistema hace sin que nadie actúe
    # ======================================================================
    def test_las_transiciones_automaticas_aparecen_en_su_diagrama(self):
        """Sin ellas, el diagrama afirma que el proceso solo avanza si alguien actúa.

        Y es falso: una evidencia caduca sola. Es de las primeras cosas que
        pregunta un auditor y de las que peor quedan si el diagrama las calla.
        """
        for auto in bpmn.TRANSICIONES_AUTOMATICAS:
            xml = self.diagramas.get(auto["document_type"])
            self.assertIsNotNone(xml, f"no hay diagrama de «{auto['document_type']}»")
            self.assertIn(auto["etiqueta"], xml,
                          f"«{auto['document_type']}» no muestra la transición automática "
                          f"«{auto['etiqueta']}»")

    def test_las_esperas_por_tiempo_llevan_reloj(self):
        """Un disparador de tiempo se dibuja con `timerEventDefinition`.

        Es lo que distingue "esto pasa cuando vence un plazo" de "esto lo lanza
        otro documento". Si se dibujaran igual, el diagrama perdería el matiz.
        """
        for auto in bpmn.TRANSICIONES_AUTOMATICAS:
            if auto["disparador"] != "timer":
                continue
            proceso = ET.fromstring(self.diagramas[auto["document_type"]]).find(f"{M}process")
            eventos = [e for e in proceso.iter(f"{M}intermediateCatchEvent")
                       if e.get("name") == auto["etiqueta"]]
            self.assertTrue(eventos, f"«{auto['etiqueta']}» no se dibujó como evento intermedio")
            for e in eventos:
                self.assertIsNotNone(e.find(f"{M}timerEventDefinition"),
                                     f"«{auto['etiqueta']}» no lleva temporizador")

    def test_el_estado_destino_automatico_existe_en_el_doctype(self):
        """Si alguien retira ese estado del DocType, esta declaración miente.

        El estado no está en el workflow (por eso hay que declararlo), así que
        nada más lo comprobaría: el diagrama seguiría dibujando una transición
        hacia un estado que ya no se puede alcanzar.
        """
        for auto in bpmn.TRANSICIONES_AUTOMATICAS:
            opciones = (frappe.get_meta(auto["document_type"])
                        .get_field("estado").options or "").split("\n")
            self.assertIn(auto["hasta"], opciones,
                          f"«{auto['document_type']}» ya no admite el estado "
                          f"«{auto['hasta']}»: la declaración está obsoleta")
            for estado in auto["desde"]:
                self.assertIn(estado, opciones,
                              f"«{auto['document_type']}» ya no admite «{estado}»")

    def test_el_codigo_que_ejecuta_la_transicion_automatica_existe(self):
        """`origen` apunta al código real: si se mueve o se borra, esto lo canta."""
        import importlib

        for auto in bpmn.TRANSICIONES_AUTOMATICAS:
            ruta = auto["origen"]
            partes = ruta.split(".")
            for corte in range(len(partes) - 1, 0, -1):
                try:
                    mod = importlib.import_module(".".join(partes[:corte]))
                except ImportError:
                    continue
                objeto = mod
                for atributo in partes[corte:]:
                    objeto = getattr(objeto, atributo, None)
                    self.assertIsNotNone(objeto, f"«{ruta}» ya no existe")
                break
            else:
                self.fail(f"no se pudo importar nada de «{ruta}»")

    def test_las_automaticas_no_se_confunden_con_las_humanas(self):
        """Van en su propio carril: nadie las ejecuta, las hace el sistema."""
        for auto in bpmn.TRANSICIONES_AUTOMATICAS:
            _nodos, _flujos, carril_de = _grafo(self.diagramas[auto["document_type"]])
            proceso = ET.fromstring(self.diagramas[auto["document_type"]]).find(f"{M}process")
            for tipo in ("intermediateCatchEvent", "serviceTask"):
                for e in proceso.iter(f"{M}{tipo}"):
                    if e.get("name") == auto["etiqueta"]:
                        self.assertEqual(carril_de.get(e.get("id")), bpmn.CARRIL_SISTEMA)

    def test_frappe_esta_disponible(self):
        """Guarda de contexto: estos tests corren dentro del sitio, no sueltos."""
        self.assertTrue(frappe.db)

    # ------------------------------------------------------------------
    # Lo que el sistema hace solo, y lo que le manda a otros procesos
    # ------------------------------------------------------------------
    def test_el_efecto_al_entrar_se_interpone_antes_del_estado(self):
        """El efecto ocurre AL llegar, así que va entre la acción y el estado.

        Sin él, el diagrama del 04 terminaba en «Cerrada» sin contar lo más
        importante que pasa ahí: que los resultados de la encuesta se publican
        como valores de indicador.
        """
        for efecto in bpmn.EFECTOS_AL_ENTRAR:
            xml = self.diagramas[efecto["document_type"]]
            _nodos, flujos, carril_de = _grafo(xml)
            proceso = ET.fromstring(xml).find(f"{M}process")
            ids = [e.get("id") for e in proceso.iter(f"{M}serviceTask")
                   if e.get("name") == efecto["etiqueta"]]
            self.assertEqual(len(ids), 1, f"{efecto['etiqueta']}: se esperaba una sola tarea")
            nid = ids[0]
            self.assertEqual(carril_de.get(nid), bpmn.CARRIL_SISTEMA,
                             "el efecto no lo ejecuta nadie: va en el carril del sistema")
            entran = [f for f in flujos if f[2] == nid]
            salen = [f for f in flujos if f[1] == nid]
            self.assertTrue(entran, "nadie llega al efecto: no está interpuesto")
            self.assertEqual(len(salen), 1, "el efecto debe continuar hacia el estado")

    def test_los_saltos_a_otro_proceso_van_a_un_pool_caja_negra(self):
        """Un mensaje necesita destinatario, y el destinatario es otro proceso.

        Se dibuja como participante sin `processRef` —la caja negra de BPMN—
        porque este diagrama no describe el interior del otro.
        """
        for salto in bpmn.SALTOS_ENTRE_PROCESOS:
            raiz = ET.fromstring(self.diagramas[salto["document_type"]])
            colab = raiz.find(f"{M}collaboration")
            cajas = {p.get("name"): p.get("id") for p in colab.iter(f"{M}participant")
                     if not p.get("processRef")}
            self.assertIn(salto["hacia"], cajas,
                          f"falta el pool de {salto['hacia']}")
            destinos = [m.get("targetRef") for m in colab.iter(f"{M}messageFlow")
                        if m.get("name") == salto["etiqueta"]]
            self.assertIn(cajas[salto["hacia"]], destinos,
                          "el mensaje no apunta al pool del proceso destino")

    def test_el_mensaje_sale_de_la_accion_que_escala(self):
        """No del estado: es al EJECUTAR la acción cuando el otro proceso recibe.

        Se resolvía con `entrada_a`, que para un estado de una sola salida
        devuelve la tarea SIGUIENTE. El 08 acababa diciendo «al cerrar un
        hallazgo ya escalado, avisa a No Conformidad» — cuando el aviso ocurre
        al escalarlo, un paso antes.
        """
        for salto in bpmn.SALTOS_ENTRE_PROCESOS:
            raiz = ET.fromstring(self.diagramas[salto["document_type"]])
            proceso, colab = raiz.find(f"{M}process"), raiz.find(f"{M}collaboration")
            nombre_de = {e.get("id"): e.get("name") for e in proceso.iter(f"{M}userTask")}
            emisores = [m.get("sourceRef") for m in colab.iter(f"{M}messageFlow")
                        if m.get("name") == salto["etiqueta"]]

            self.assertEqual(len(emisores), 1,
                             f"«{salto['etiqueta']}» debe salir de un solo sitio en "
                             f"{salto['document_type']}")
            if salto["accion"] is None:
                # sin acción de workflow: lo manda el pool, no un nodo suyo
                self.assertIsNone(nombre_de.get(emisores[0]))
            else:
                self.assertEqual(nombre_de.get(emisores[0]), salto["accion"])

    def test_cada_salto_declarado_existe_de_verdad_en_el_codigo(self):
        """Regla de admisión: no se dibuja un salto que nadie ejecuta."""
        import importlib
        for salto in bpmn.SALTOS_ENTRE_PROCESOS:
            partes = salto["origen"].split(".")
            for corte in range(len(partes) - 1, 0, -1):
                try:
                    objeto = importlib.import_module(".".join(partes[:corte]))
                except ImportError:
                    continue
                for atributo in partes[corte:]:
                    objeto = getattr(objeto, atributo, None)
                    self.assertIsNotNone(objeto, f"«{salto['origen']}» ya no existe")
                break
            else:
                self.fail(f"no se pudo importar nada de «{salto['origen']}»")

    def test_un_diagrama_sin_saltos_no_gana_pools_de_mas(self):
        """Solo llevan caja negra los que de verdad mandan algo."""
        con_saltos = {s["document_type"] for s in bpmn.SALTOS_ENTRE_PROCESOS}
        for dt, xml in self.diagramas.items():
            if dt in con_saltos:
                continue
            colab = ET.fromstring(xml).find(f"{M}collaboration")
            sueltos = [p.get("name") for p in colab.iter(f"{M}participant")
                       if not p.get("processRef")]
            self.assertEqual(sueltos, [], f"{dt} tiene pools que no le corresponden")

    # ------------------------------------------------------------------
    # El dibujo también dice cosas: dónde está un nodo significa quién lo hace
    # ------------------------------------------------------------------
    def _cajas(self, xml):
        """Bounds por id y el carril al que pertenece cada nodo."""
        raiz = ET.fromstring(xml)
        proceso = raiz.find(f"{M}process")
        plano = raiz.find(f".//{DI}BPMNPlane")
        carril_de = {}
        for lane in proceso.iter(f"{M}lane"):
            for ref in lane.iter(f"{M}flowNodeRef"):
                carril_de[ref.text] = lane.get("id")
        cajas = {}
        for shape in plano.iter(f"{DI}BPMNShape"):
            b = shape.find(f"{DC}Bounds")
            if b is not None:
                cajas[shape.get("bpmnElement")] = tuple(
                    float(b.get(k)) for k in ("x", "y", "width", "height"))
        return cajas, carril_de

    def test_cada_nodo_se_dibuja_dentro_de_su_carril(self):
        """Un nodo en el carril del vecino dice quién lo ejecuta, y lo dice mal.

        Nueve de los quince diagramas tenían nodos fuera de su banda el
        2026-08-23: el generador conservaba el layout guardado nodo a nodo, y
        esas posiciones dejan de valer en cuanto cambia el reparto de carriles.
        """
        for dt, xml in self.diagramas.items():
            cajas, carril_de = self._cajas(xml)
            for nid, lane_id in carril_de.items():
                if nid not in cajas or lane_id not in cajas:
                    continue
                _x, y, _w, alto = cajas[nid]
                _lx, ly, _lw, lalto = cajas[lane_id]
                self.assertGreaterEqual(y, ly, f"{dt}: «{nid}» se sale por arriba")
                self.assertLessEqual(y + alto, ly + lalto,
                                     f"{dt}: «{nid}» se sale por abajo")

    def test_no_hay_dos_nodos_dibujados_uno_encima_de_otro(self):
        """Dos tareas en la misma caja son una tarea invisible."""
        for dt, xml in self.diagramas.items():
            cajas, _carril = self._cajas(xml)
            nodos = {k: v for k, v in cajas.items()
                     if not k.startswith(("Participant_", "Lane_"))}
            ids = sorted(nodos)
            for i, a in enumerate(ids):
                ax, ay, aw, ah = nodos[a]
                for b in ids[i + 1:]:
                    bx, by, bw, bh = nodos[b]
                    se_pisan = (ax < bx + bw and bx < ax + aw
                                and ay < by + bh and by < ay + ah)
                    self.assertFalse(se_pisan, f"{dt}: «{a}» y «{b}» se solapan")

