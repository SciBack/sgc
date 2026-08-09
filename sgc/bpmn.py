# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

"""Exporta un workflow del sistema a BPMN 2.0 (OMG).

Por qué existe: el área de calidad trabaja con BPMN, que es la notación de la
gestión por procesos, y el motor de workflow del framework habla otro idioma
(estados, acciones, roles). Este módulo traduce de aquel a este.

**Traduce, no reimplementa.** La fuente de verdad sigue siendo la definición del
workflow en `sgc/setup/f*_workflow*.py`; el BPMN es una vista derivada. Si el
diagrama y el código discrepan, el que está mal es el diagrama, y se arregla
regenerándolo.

Cómo se corresponden los dos modelos:

    estado                -> bpmn:userTask   (el documento espera a que alguien actúe)
    estado inicial        -> bpmn:startEvent + el userTask correspondiente
    estado sin salidas    -> el userTask + bpmn:endEvent
    transición            -> bpmn:sequenceFlow, con la acción como nombre
    estado con N salidas  -> bpmn:exclusiveGateway, porque son excluyentes entre sí
    rol que edita         -> bpmn:lane (el carril donde vive la tarea)

Lo que NO es estándar (qué rol ejecuta cada transición y si permite
autoaprobación) viaja en `extensionElements`, que es el mecanismo que BPMN
prevé para esto. **Ojo:** algunas herramientas de terceros descartan las
extensiones ajenas al guardar. Antes de confiar en un ida y vuelta, hay que
comprobar que sobreviven.

Límite conocido y deliberado: BPMN es más expresivo que el motor de workflow del
framework. Todo workflow se puede dibujar en BPMN, pero no todo BPMN se puede
ejecutar aquí (gateways paralelos, temporizadores, subprocesos). La traducción
inversa tiene que rechazar lo que no sea representable en vez de ignorarlo.
"""

import unicodedata
from xml.sax.saxutils import escape, quoteattr

NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
    "sgc": "https://sciback.com/schema/sgc/1.0",
}

# Geometría del lienzo. Son números elegidos para que el resultado sea legible al
# abrirlo, no una maqueta: cualquier modelador permite recolocar después.
ANCHO_TAREA, ALTO_TAREA = 120, 80
LADO_EVENTO, LADO_GATEWAY = 36, 50
PASO_X = 200          # separación entre columnas
ALTO_CARRIL = 160
X_ORIGEN, Y_ORIGEN = 200, 80
ANCHO_ETIQUETA = 30   # margen izquierdo del pool para el nombre vertical


def specs_de_workflows():
    """Descubre las definiciones de workflow declaradas en `sgc/setup/`.

    Una definición es cualquier diccionario de nivel de módulo que tenga
    `document_type`, `states` y `transitions`. Se descubren en vez de listarse a
    mano para que un workflow nuevo entre solo: una lista fija se queda corta en
    silencio, que es justo como trece de ellos llevaban sin documentar.

    Devuelve [(nombre_modulo, spec)], sin duplicados por DocType.
    """
    import importlib
    import pathlib

    aqui = pathlib.Path(__file__).parent / "setup"
    vistos, encontradas = set(), []
    for archivo in sorted(aqui.glob("f*workflow*.py")):
        try:
            mod = importlib.import_module(f"sgc.setup.{archivo.stem}")
        except Exception:
            # Un módulo que no importa no debe tumbar la exportación del resto,
            # pero tampoco desaparecer sin dejar rastro.
            print(f"  [SKIP] no se pudo importar {archivo.name}")
            continue
        for nombre in dir(mod):
            valor = getattr(mod, nombre)
            if (isinstance(valor, dict) and "document_type" in valor
                    and "states" in valor and "transitions" in valor):
                if valor["document_type"] in vistos:
                    continue
                vistos.add(valor["document_type"])
                encontradas.append((archivo.stem, valor))
    return encontradas


def nombre_archivo(document_type):
    """`No Conformidad` -> `no-conformidad.bpmn`."""
    limpio = "".join(c.lower() if c.isalnum() else "-" for c in document_type)
    while "--" in limpio:
        limpio = limpio.replace("--", "-")
    return limpio.strip("-") + ".bpmn"


def exportar_todos(destino):
    """Escribe un `.bpmn` por cada workflow declarado. Devuelve el informe."""
    import pathlib

    dir_destino = pathlib.Path(destino)
    dir_destino.mkdir(parents=True, exist_ok=True)
    informe = []
    for modulo, spec in specs_de_workflows():
        ruta = dir_destino / nombre_archivo(spec["document_type"])
        ruta.write_text(construir(spec), encoding="utf-8")
        informe.append({
            "document_type": spec["document_type"],
            "estados": len(spec["states"]),
            "transiciones": len(spec["transitions"]),
            "modulo": modulo,
            "archivo": ruta.name,
        })
    return informe


def _id(prefijo, texto, usados=None):
    """Identificador XML estable y legible a partir de un nombre de negocio.

    `xs:ID` exige unicidad en todo el documento. Si se pasa `usados`, el
    identificador se sufija hasta ser único: hay workflows con DOS transiciones
    del mismo estado, con la misma acción y distinto rol autorizado (el patrón de
    doble aprobación), y sin esto ambas colisionarían en el mismo id y el fichero
    dejaría de validar.
    """
    # Los identificadores tienen que ser ASCII PURO. El XSD de la OMG acepta
    # `ñ` y tildes (XML permite letras Unicode en un NCName), pero bpmn-moddle
    # —la librería que usan bpmn-js, Camunda Modeler y casi todo el ecosistema—
    # los rechaza con "illegal ID" y descarta el elemento entero. Ojo con el
    # atajo `str.isalnum()`: en Python "ñ".isalnum() es True.
    # Solo se transliteran los IDs; el `name` visible conserva sus tildes.
    normal = unicodedata.normalize("NFKD", str(texto))
    sin_tildes = "".join(c for c in normal if not unicodedata.combining(c))
    limpio = "".join(c if (c.isascii() and c.isalnum()) else "_" for c in sin_tildes)
    base = f"{prefijo}_{limpio}"
    if usados is None:
        return base
    candidato, n = base, 2
    while candidato in usados:
        candidato, n = f"{base}_{n}", n + 1
    usados.add(candidato)
    return candidato


def _centro(x, y, ancho, alto):
    return x + ancho / 2, y + alto / 2


class _Nodo:
    """Un elemento del diagrama, con su geometría ya resuelta."""

    def __init__(self, nid, tipo, nombre, carril, col, fila):
        self.id = nid
        self.tipo = tipo          # userTask | startEvent | endEvent | exclusiveGateway
        self.nombre = nombre
        self.carril = carril
        self.col = col
        self.fila = fila

    @property
    def ancho(self):
        return {"userTask": ANCHO_TAREA, "exclusiveGateway": LADO_GATEWAY}.get(
            self.tipo, LADO_EVENTO)

    @property
    def alto(self):
        return {"userTask": ALTO_TAREA, "exclusiveGateway": LADO_GATEWAY}.get(
            self.tipo, LADO_EVENTO)

    @property
    def x(self):
        return X_ORIGEN + ANCHO_ETIQUETA + self.col * PASO_X

    @property
    def y(self):
        # centrado verticalmente dentro de su carril
        base = Y_ORIGEN + self.fila * ALTO_CARRIL
        return base + (ALTO_CARRIL - self.alto) / 2


def _ordenar_por_alcance(estados, transiciones, inicial, carril_de=None):
    """Columna de cada estado = distancia en pasos desde el estado inicial.

    Un recorrido en anchura basta y da un orden estable: los estados a los que
    solo se llega retrocediendo (devoluciones) conservan la columna de su primera
    aparición, que es lo que hace legible el diagrama.

    Con una excepción que mejora mucho el resultado: **si el paso cambia de
    carril, el destino se queda en la MISMA columna**. Así el flujo baja en
    vertical al carril de abajo en vez de irse en diagonal hacia la derecha, que
    es lo que hace que un diagrama con varios responsables se lea de un vistazo.
    """
    salidas = {}
    for desde, _accion, hacia, *_resto in transiciones:
        salidas.setdefault(desde, []).append(hacia)

    carril_de = carril_de or {}
    columna = {inicial: 0}
    cola = [inicial]
    while cola:
        actual = cola.pop(0)
        for siguiente in salidas.get(actual, []):
            if siguiente not in columna:
                cambia_de_carril = (carril_de.get(siguiente) != carril_de.get(actual))
                columna[siguiente] = columna[actual] + (0 if cambia_de_carril else 1)
                cola.append(siguiente)
    # estados inalcanzables: se colocan al final en vez de descartarlos en silencio
    for estado in estados:
        columna.setdefault(estado, max(columna.values(), default=0) + 1)
    return columna


def construir(spec):
    """Devuelve el XML BPMN 2.0 de un workflow.

    `spec` es el diccionario que define el workflow: `name`, `document_type`,
    `states` [(estado, doc_status, rol_editor)] y `transitions`
    [(desde, accion, hacia, rol[, autoaprobacion])].
    """
    estados = [e[0] for e in spec["states"]]
    editor_de = {e[0]: e[2] for e in spec["states"]}
    transiciones = spec["transitions"]
    inicial = estados[0]

    # Carriles: un rol por carril, en el orden en que aparecen en los estados.
    carriles = []
    for estado in estados:
        if editor_de[estado] not in carriles:
            carriles.append(editor_de[estado])
    fila_de = {rol: i for i, rol in enumerate(carriles)}

    columna = _ordenar_por_alcance(estados, transiciones, inicial, editor_de)
    salidas = {}
    for t in transiciones:
        salidas.setdefault(t[0], []).append(t)

    nodos, flujos = {}, []
    ids_usados = set()

    # El evento de inicio ocupa la columna 0 y los estados se corren una a la
    # derecha: si el inicio fuera a la columna -1 quedaría FUERA del pool, con la
    # primera flecha entrando desde la nada.
    nid_inicio = "StartEvent_1"
    nodos[nid_inicio] = _Nodo(nid_inicio, "startEvent", "Inicio",
                              editor_de[inicial], 0.35, fila_de[editor_de[inicial]])

    # Una tarea por estado
    for estado in estados:
        nid = _id("Task", estado)
        nodos[nid] = _Nodo(nid, "userTask", estado, editor_de[estado],
                           columna[estado] + 1, fila_de[editor_de[estado]])
    flujos.append((_id("Flow", "inicio", ids_usados), nid_inicio, _id("Task", inicial), "", None))

    for estado in estados:
        salientes = salidas.get(estado, [])
        origen = _id("Task", estado)

        if not salientes:
            # estado terminal: se cierra con un evento de fin
            nid_fin = _id("End", estado)
            nodos[nid_fin] = _Nodo(nid_fin, "endEvent", "Fin", editor_de[estado],
                                   columna[estado] + 2, fila_de[editor_de[estado]])
            flujos.append((_id("Flow", f"fin_{estado}", ids_usados), origen, nid_fin, "", None))
            continue

        if len(salientes) > 1:
            # varias salidas excluyentes: en BPMN eso es un gateway exclusivo, no
            # varias flechas sueltas saliendo de la tarea
            # Media columna a la derecha de su tarea: en la misma columna se
            # solapaba con ella y el diagrama salía ilegible.
            nid_gw = _id("Gateway", estado)
            nodos[nid_gw] = _Nodo(nid_gw, "exclusiveGateway", "", editor_de[estado],
                                  columna[estado] + 1.5, fila_de[editor_de[estado]])
            flujos.append((_id("Flow", f"gw_{estado}", ids_usados), origen, nid_gw, "", None))
            origen = nid_gw

        for t in salientes:
            desde, accion, hacia, rol = t[0], t[1], t[2], t[3]
            autoaprob = t[4] if len(t) > 4 else 0
            flujos.append((
                _id("Flow", f"{desde}__{accion}", ids_usados),
                origen, _id("Task", hacia), accion,
                {"rol": rol, "autoaprobacion": autoaprob},
            ))

    return _serializar(spec, carriles, nodos, flujos)


def _serializar(spec, carriles, nodos, flujos):
    proc_id = _id("Process", spec["document_type"])
    part_id = _id("Participant", spec["document_type"])
    collab_id = "Collaboration_1"

    ancho_max = max((n.x + n.ancho for n in nodos.values()), default=800)
    alto_pool = len(carriles) * ALTO_CARRIL
    ancho_pool = ancho_max - X_ORIGEN + 80

    o = []
    a = o.append
    a('<?xml version="1.0" encoding="UTF-8"?>')
    a("<bpmn:definitions " + " ".join(f'xmlns:{k}={quoteattr(v)}' for k, v in NS.items())
      + ' id="Definitions_1"'
      + f' targetNamespace={quoteattr(NS["sgc"])}'
      + ' exporter="SGC" exporterVersion="1.0">')

    a(f'  <bpmn:collaboration id="{collab_id}">')
    a(f'    <bpmn:participant id="{part_id}" name={quoteattr(spec["name"])} processRef="{proc_id}" />')
    a("  </bpmn:collaboration>")

    a(f'  <bpmn:process id="{proc_id}" isExecutable="false">')
    a('    <bpmn:laneSet id="LaneSet_1">')
    for rol in carriles:
        a(f'      <bpmn:lane id="{_id("Lane", rol)}" name={quoteattr(rol)}>')
        for n in nodos.values():
            if n.carril == rol:
                a(f"        <bpmn:flowNodeRef>{n.id}</bpmn:flowNodeRef>")
        a("      </bpmn:lane>")
    a("    </bpmn:laneSet>")

    entrantes, salientes = {}, {}
    for fid, src, tgt, _nombre, _ext in flujos:
        salientes.setdefault(src, []).append(fid)
        entrantes.setdefault(tgt, []).append(fid)

    for n in nodos.values():
        etiqueta = f" name={quoteattr(n.nombre)}" if n.nombre else ""
        a(f"    <bpmn:{n.tipo} id=\"{n.id}\"{etiqueta}>")
        for fid in entrantes.get(n.id, []):
            a(f"      <bpmn:incoming>{fid}</bpmn:incoming>")
        for fid in salientes.get(n.id, []):
            a(f"      <bpmn:outgoing>{fid}</bpmn:outgoing>")
        a(f"    </bpmn:{n.tipo}>")

    for fid, src, tgt, nombre, ext in flujos:
        etiqueta = f" name={quoteattr(nombre)}" if nombre else ""
        a(f'    <bpmn:sequenceFlow id="{fid}" sourceRef="{src}" targetRef="{tgt}"{etiqueta}>')
        if ext:
            # Metadatos propios: el rol autorizado y si la transición admite que la
            # ejecute quien creó el documento. No son BPMN estándar; van aquí
            # porque es el punto de extensión que la norma reserva para esto.
            a("      <bpmn:extensionElements>")
            a(f'        <sgc:transicion rol={quoteattr(ext["rol"])} '
              f'autoaprobacion="{int(ext["autoaprobacion"] or 0)}" />')
            a("      </bpmn:extensionElements>")
        a("    </bpmn:sequenceFlow>")
    a("  </bpmn:process>")

    # --- Diagrama (posiciones). Sin esto, un modelador no tiene qué dibujar ---
    a('  <bpmndi:BPMNDiagram id="Diagram_1">')
    a(f'    <bpmndi:BPMNPlane id="Plane_1" bpmnElement="{collab_id}">')
    a(f'      <bpmndi:BPMNShape id="Shape_{part_id}" bpmnElement="{part_id}" isHorizontal="true">')
    a(f'        <dc:Bounds x="{X_ORIGEN}" y="{Y_ORIGEN}" width="{ancho_pool}" height="{alto_pool}" />')
    a("      </bpmndi:BPMNShape>")
    for i, rol in enumerate(carriles):
        y = Y_ORIGEN + i * ALTO_CARRIL
        a(f'      <bpmndi:BPMNShape id="Shape_{_id("Lane", rol)}" '
          f'bpmnElement="{_id("Lane", rol)}" isHorizontal="true">')
        a(f'        <dc:Bounds x="{X_ORIGEN + ANCHO_ETIQUETA}" y="{y}" '
          f'width="{ancho_pool - ANCHO_ETIQUETA}" height="{ALTO_CARRIL}" />')
        a("      </bpmndi:BPMNShape>")
    for n in nodos.values():
        a(f'      <bpmndi:BPMNShape id="Shape_{n.id}" bpmnElement="{n.id}">')
        a(f'        <dc:Bounds x="{int(n.x)}" y="{int(n.y)}" '
          f'width="{n.ancho}" height="{n.alto}" />')
        a("      </bpmndi:BPMNShape>")
    for fid, src, tgt, _nombre, _ext in flujos:
        ns, nt = nodos[src], nodos[tgt]
        cx1, cy1 = _centro(ns.x, ns.y, ns.ancho, ns.alto)
        cx2, cy2 = _centro(nt.x, nt.y, nt.ancho, nt.alto)
        # Salir por el borde, no por el centro: una flecha centro a centro
        # atraviesa las dos cajas y el diagrama se lee mal. Si el destino está a
        # la izquierda (una devolución), se sale por el borde contrario.
        a(f'      <bpmndi:BPMNEdge id="Edge_{fid}" bpmnElement="{fid}">')
        if ns.fila == nt.fila:
            # mismo carril: recta horizontal de borde a borde
            if cx2 >= cx1:
                x1, x2 = ns.x + ns.ancho, nt.x
            else:
                x1, x2 = ns.x, nt.x + nt.ancho
            a(f'        <di:waypoint x="{int(x1)}" y="{int(cy1)}" />')
            a(f'        <di:waypoint x="{int(x2)}" y="{int(cy2)}" />')
        else:
            # cambia de carril: codo en L. Sale por arriba o por abajo, recorre
            # el desnivel en vertical y entra por el lado del destino. Una recta
            # diagonal entre dos carriles cruza el resto del dibujo.
            y1 = ns.y + ns.alto if nt.fila > ns.fila else ns.y
            x2 = nt.x if cx2 >= cx1 else nt.x + nt.ancho
            a(f'        <di:waypoint x="{int(cx1)}" y="{int(y1)}" />')
            a(f'        <di:waypoint x="{int(cx1)}" y="{int(cy2)}" />')
            a(f'        <di:waypoint x="{int(x2)}" y="{int(cy2)}" />')
        a("      </bpmndi:BPMNEdge>")
    a("    </bpmndi:BPMNPlane>")
    a("  </bpmndi:BPMNDiagram>")
    a("</bpmn:definitions>")
    return "\n".join(o) + "\n"
