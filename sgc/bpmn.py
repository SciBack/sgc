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


# ===========================================================================
# Transiciones que el sistema hace SOLO, fuera del motor de workflow.
#
# El motor bloquea, a nivel de máquina de estados, cualquier transición que no
# esté en su grafo. Por eso estos cambios se escriben directo a la base de datos:
# son estados que pone el sistema, nunca una persona. Y por eso NO aparecen en la
# definición del workflow y hay que declararlos aquí.
#
# Sin esto, un diagrama afirma que el proceso solo avanza cuando alguien actúa, y
# es falso: una evidencia caduca sola. Es justo lo que un auditor pregunta.
#
# `disparador`: "timer" (pasa el tiempo) o "mensaje" (lo provoca otro documento).
# `origen` apunta al código que la ejecuta: si se mueve, el test lo detecta.
# ===========================================================================
TRANSICIONES_AUTOMATICAS = [
    {
        "document_type": "Evidencia",
        "desde": ("Pendiente", "Valida"),
        "hasta": "Vencida",
        "disparador": "timer",
        "etiqueta": "Vence la vigencia",
        "origen": "sgc.tasks.marcar_evidencias_vencidas",
    },
    {
        "document_type": "Documento Controlado",
        "desde": ("Publicado",),
        "hasta": "Obsoleto",
        "disparador": "mensaje",
        "etiqueta": "Otro documento lo reemplaza",
        "origen": "sgc.sgc_nucleo.doctype.documento_controlado.documento_controlado"
                  ".DocumentoControlado._obsoletar_reemplazado",
    },
]

CARRIL_SISTEMA = "Sistema (automático)"


def automaticas_de(document_type):
    """Transiciones automáticas declaradas para un DocType."""
    return [a for a in TRANSICIONES_AUTOMATICAS if a["document_type"] == document_type]


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


def layout_de(xml):
    """Extrae las posiciones de un `.bpmn` ya existente: {id: (x, y, w, h)}.

    Sirve para NO pisar el trabajo de quien recolocó el diagrama a mano. Un
    generador que reimpone su propio layout en cada corrida obliga a repetir esa
    edición cada vez que cambia el proceso, y entonces nadie la hace.
    """
    import re

    posiciones = {}
    patron = re.compile(
        r'bpmnElement="([^"]+)"[^>]*>\s*<dc:Bounds\s+x="([-\d.]+)"\s+y="([-\d.]+)"'
        r'\s+width="([\d.]+)"\s+height="([\d.]+)"')
    for m in patron.finditer(xml or ""):
        posiciones[m.group(1)] = tuple(float(v) for v in m.groups()[1:])
    return posiciones


def exportar_todos(destino, preservar_layout=True):
    """Escribe un `.bpmn` por cada workflow declarado. Devuelve el informe.

    Con `preservar_layout`, las posiciones de un fichero ya existente se
    conservan y solo se calculan las de los elementos nuevos. Así la semántica
    (que sale del código) se actualiza sola sin destruir el ajuste visual (que
    lo hace una persona con criterio).
    """
    import pathlib

    dir_destino = pathlib.Path(destino)
    dir_destino.mkdir(parents=True, exist_ok=True)
    informe = []
    for modulo, spec in specs_de_workflows():
        ruta = dir_destino / nombre_archivo(spec["document_type"])
        previo = {}
        if preservar_layout and ruta.exists():
            previo = layout_de(ruta.read_text(encoding="utf-8"))
        xml = construir(spec, layout_previo=previo)
        ruta.write_text(xml, encoding="utf-8")
        informe.append({
            "document_type": spec["document_type"],
            "estados": len(spec["states"]),
            "transiciones": len(spec["transitions"]),
            "modulo": modulo,
            "archivo": ruta.name,
            "posiciones_conservadas": len(previo),
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


def _columnas_por_alcance(nodos_ids, flujos, inicio):
    """Columna de cada nodo = distancia en pasos desde el inicio.

    Recorrido en anchura sobre el grafo REAL de nodos (no sobre los estados):
    así los retrocesos conservan la columna de su primera aparición, que es lo
    que mantiene el diagrama legible en vez de estirarlo por cada devolución.
    """
    salidas = {}
    for _fid, src, tgt, _n, _e in flujos:
        salidas.setdefault(src, []).append(tgt)
    col = {inicio: 0}
    cola = [inicio]
    while cola:
        actual = cola.pop(0)
        for sig in salidas.get(actual, []):
            if sig not in col:
                col[sig] = col[actual] + 1
                cola.append(sig)
    for nid in nodos_ids:
        col.setdefault(nid, max(col.values(), default=0) + 1)
    return col


def construir(spec, layout_previo=None):
    """Devuelve el XML BPMN 2.0 de un workflow.

    **La tarea es la ACCIÓN, no el estado.** En BPMN una `userTask` es una
    actividad y se lee como un verbo: "Consolidar", "Enviar a revisión". Un
    estado ("En revisión") no es algo que alguien haga, es donde el documento
    espera; dibujarlo como tarea produce un diagrama que valida contra el
    esquema pero que a quien lee procesos le resulta ajeno.

    De ahí el mapeo:

        transición                 -> userTask con el nombre de la acción,
                                      en el carril de quien la EJECUTA
        estado con varias salidas  -> exclusiveGateway con el nombre del estado
                                      (es donde se decide)
        estado con una sola salida -> no se dibuja: encadena directo
        estado sin salidas         -> endEvent

    El carril es el rol AUTORIZADO a ejecutar la acción, no el que puede editar
    el documento: es lo que de verdad gobierna quién puede mover el proceso, y
    hace visible la segregación de funciones.

    `layout_previo` ({id: (x, y, w, h)}) conserva posiciones ya ajustadas a mano.
    """
    estados = [e[0] for e in spec["states"]]
    transiciones = spec["transitions"]
    inicial = estados[0]

    salidas = {}
    for t in transiciones:
        salidas.setdefault(t[0], []).append(t)

    # Carriles: el rol que ejecuta cada acción, en orden de aparición.
    carriles = []
    for t in transiciones:
        if t[3] not in carriles:
            carriles.append(t[3])
    if not carriles:
        carriles = ["Sistema"]
    automaticas = automaticas_de(spec["document_type"])
    if automaticas and CARRIL_SISTEMA not in carriles:
        carriles.append(CARRIL_SISTEMA)   # abajo del todo: no lo ejecuta nadie
    fila_de = {rol: i for i, rol in enumerate(carriles)}
    # (el carril del sistema ya está incluido si hay transiciones automáticas)

    usados = set()
    id_tarea = {}      # (estado_origen, accion, indice) -> id
    for i, t in enumerate(transiciones):
        id_tarea[i] = _id("Task", f"{t[0]}__{t[1]}", usados)
    id_gw = {e: _id("Gateway", e, usados) for e in estados if len(salidas.get(e, [])) > 1}
    id_fin = {e: _id("End", e, usados) for e in estados if not salidas.get(e)}

    def entrada_a(estado):
        """Nodo que representa 'el documento llega a este estado'."""
        if estado in id_gw:
            return id_gw[estado]
        if salidas.get(estado):
            return id_tarea[transiciones.index(salidas[estado][0])]
        return id_fin[estado]

    nodos, flujos = {}, []
    nid_inicio = "StartEvent_1"

    for i, t in enumerate(transiciones):
        rol = t[3]
        nodos[id_tarea[i]] = _Nodo(id_tarea[i], "userTask", t[1], rol, 0, fila_de[rol])
    for estado, gid in id_gw.items():
        rol = salidas[estado][0][3]          # quien decide es quien puede actuar
        nodos[gid] = _Nodo(gid, "exclusiveGateway", estado, rol, 0, fila_de[rol])
    for estado, eid in id_fin.items():
        llegan = [t for t in transiciones if t[2] == estado]
        rol = llegan[0][3] if llegan else carriles[0]
        nodos[eid] = _Nodo(eid, "endEvent", estado, rol, 0, fila_de[rol])
    rol_inicio = salidas[inicial][0][3] if salidas.get(inicial) else carriles[0]
    nodos[nid_inicio] = _Nodo(nid_inicio, "startEvent", "Inicio", rol_inicio, 0,
                              fila_de[rol_inicio])

    flujos.append((_id("Flow", "inicio", usados), nid_inicio, entrada_a(inicial), "", None))

    # --- lo que ocurre sin que nadie actúe ---
    fin_automatico = {}   # un solo final por estado destino, no uno por origen
    for auto in automaticas:
        tipo = "intermediateCatchEvent" if auto["disparador"] == "timer" else "serviceTask"
        for estado_origen in auto["desde"]:
            if estado_origen not in estados:
                continue          # el estado ya no existe: se omite, no se inventa
            nid = _id("Auto", f"{estado_origen}__{auto['hasta']}", usados)
            nodos[nid] = _Nodo(nid, tipo, auto["etiqueta"], CARRIL_SISTEMA, 0,
                               fila_de[CARRIL_SISTEMA])
            nodos[nid].disparador = auto["disparador"]
            destino = (id_fin[auto["hasta"]] if auto["hasta"] in id_fin
                       else entrada_a(auto["hasta"]) if auto["hasta"] in estados
                       else None)
            if destino is None:
                # el estado destino no está en el workflow (es el caso normal:
                # son estados que solo pone el sistema). Se dibuja su propio fin,
                # UNO por estado: "Vencida" es un estado, no uno por cada origen.
                if auto["hasta"] not in fin_automatico:
                    nid_f = _id("End", auto["hasta"], usados)
                    nodos[nid_f] = _Nodo(nid_f, "endEvent", auto["hasta"],
                                         CARRIL_SISTEMA, 0, fila_de[CARRIL_SISTEMA])
                    fin_automatico[auto["hasta"]] = nid_f
                destino = fin_automatico[auto["hasta"]]
            flujos.append((_id("Flow", f"auto_in_{estado_origen}_{auto['hasta']}", usados),
                           entrada_a(estado_origen), nid, "", None))
            flujos.append((_id("Flow", f"auto_out_{estado_origen}_{auto['hasta']}", usados),
                           nid, destino, "", None))
    for i, t in enumerate(transiciones):
        tid = id_tarea[i]
        if t[0] in id_gw:
            # el rombo reparte hacia cada acción posible
            flujos.append((_id("Flow", f"gw_{t[0]}_{t[1]}", usados), id_gw[t[0]], tid, "", None))
        flujos.append((
            _id("Flow", f"{t[0]}_{t[1]}_hacia_{t[2]}", usados), tid, entrada_a(t[2]), "",
            {"rol": t[3], "autoaprobacion": t[4] if len(t) > 4 else 0},
        ))

    # --- posiciones: columna por alcance, fila por carril, sin solapes ---
    col = _columnas_por_alcance(list(nodos), flujos, nid_inicio)
    ocupadas = set()
    for nid in sorted(nodos, key=lambda n: (col[n], nodos[n].fila)):
        n = nodos[nid]
        c = col[nid]
        while (c, n.fila) in ocupadas:   # dos nodos del mismo carril y columna
            c += 1                       # se pisarían: se corre el segundo
        ocupadas.add((c, n.fila))
        n.col = c

    return _serializar(spec, carriles, nodos, flujos, layout_previo or {})


def _serializar(spec, carriles, nodos, flujos, layout_previo=None):
    layout_previo = layout_previo or {}

    def geom(nodo):
        """Posición del nodo: la ajustada a mano si existe, si no la calculada."""
        if nodo.id in layout_previo:
            return layout_previo[nodo.id]
        return (nodo.x, nodo.y, nodo.ancho, nodo.alto)
    proc_id = _id("Process", spec["document_type"])
    part_id = _id("Participant", spec["document_type"])
    collab_id = "Collaboration_1"

    ancho_max = max((geom(n)[0] + geom(n)[2] for n in nodos.values()), default=800)
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
        if getattr(n, "disparador", None) == "timer":
            # el reloj dentro del círculo: esto ocurre porque pasa el tiempo
            a(f'      <bpmn:timerEventDefinition id="Timer_{n.id}" />')
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
        gx, gy, gw, gh = geom(n)
        a(f'      <bpmndi:BPMNShape id="Shape_{n.id}" bpmnElement="{n.id}">')
        a(f'        <dc:Bounds x="{int(gx)}" y="{int(gy)}" '
          f'width="{int(gw)}" height="{int(gh)}" />')
        a("      </bpmndi:BPMNShape>")
    for fid, src, tgt, _nombre, _ext in flujos:
        ns, nt = nodos[src], nodos[tgt]
        sx, sy, sw, sh = geom(ns)
        tx, ty, tw, th = geom(nt)
        cx1, cy1 = _centro(sx, sy, sw, sh)
        cx2, cy2 = _centro(tx, ty, tw, th)
        # Salir por el borde, no por el centro: una flecha centro a centro
        # atraviesa las dos cajas y el diagrama se lee mal. Si el destino está a
        # la izquierda (una devolución), se sale por el borde contrario.
        a(f'      <bpmndi:BPMNEdge id="Edge_{fid}" bpmnElement="{fid}">')
        if abs(cy1 - cy2) < 1:
            # misma altura: recta horizontal de borde a borde
            if cx2 >= cx1:
                x1, x2 = sx + sw, tx
            else:
                x1, x2 = sx, tx + tw
            a(f'        <di:waypoint x="{int(x1)}" y="{int(cy1)}" />')
            a(f'        <di:waypoint x="{int(x2)}" y="{int(cy2)}" />')
        else:
            # cambia de carril: codo en L. Sale por arriba o por abajo, recorre
            # el desnivel en vertical y entra por el lado del destino. Una recta
            # diagonal entre dos carriles cruza el resto del dibujo.
            y1 = sy + sh if cy2 > cy1 else sy
            x2 = tx if cx2 >= cx1 else tx + tw
            a(f'        <di:waypoint x="{int(cx1)}" y="{int(y1)}" />')
            a(f'        <di:waypoint x="{int(cx1)}" y="{int(cy2)}" />')
            a(f'        <di:waypoint x="{int(x2)}" y="{int(cy2)}" />')
        a("      </bpmndi:BPMNEdge>")
    a("    </bpmndi:BPMNPlane>")
    a("  </bpmndi:BPMNDiagram>")
    a("</bpmn:definitions>")
    return "\n".join(o) + "\n"
