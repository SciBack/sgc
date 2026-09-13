"""Controles del editor manual BPMN. No demuestra equivalencia semántica de workflows."""
import re
from xml.etree import ElementTree as ET

MAX_BYTES_BPMN = 2 * 1024 * 1024
MODEL = 'http://www.omg.org/spec/BPMN/20100524/MODEL'
DI = 'http://www.omg.org/spec/BPMN/20100524/DI'
NAMESPACES = {MODEL, DI, 'http://www.omg.org/spec/DD/20100524/DC',
              'http://www.omg.org/spec/DD/20100524/DI'}
ATTRIBUTE_NAMESPACES = NAMESPACES | {'http://www.w3.org/2001/XMLSchema-instance',
                                   'http://www.w3.org/XML/1998/namespace'}
FLOW_NODES = {'task', 'userTask', 'manualTask', 'serviceTask', 'sendTask', 'receiveTask',
              'businessRuleTask', 'subProcess', 'callActivity', 'transaction',
              'startEvent', 'endEvent', 'intermediateCatchEvent', 'intermediateThrowEvent',
              'boundaryEvent', 'exclusiveGateway', 'inclusiveGateway', 'parallelGateway',
              'complexGateway', 'eventBasedGateway'}
TEXT_REFS = {'incoming', 'outgoing', 'flowNodeRef', 'sourceRef', 'targetRef',
             'dataInputRefs', 'dataOutputRefs', 'inputSetRefs', 'outputSetRefs',
             'supportedInterfaceRef', 'eventDefinitionRef'}


def _nombre(tag):
    if tag.startswith('{'):
        namespace, local = tag[1:].split('}', 1)
        return namespace, local
    return '', tag


def validar_bpmn(xml, max_bytes=MAX_BYTES_BPMN):
    """Valida un documento manual y devuelve sus bytes UTF-8 sin reserializarlo.

    DTD/entidades, scripts/extensiones de ejecución, diagramas SGC generados y
    referencias no locales quedan fuera del editor. schemaLocation no se carga:
    ElementTree no descarga esquemas ni recursos de red. Los atributos name y
    documentation son texto; no se buscan palabras ejecutables dentro de ellos.
    """
    try:
        if isinstance(xml, bytes):
            if len(xml) > max_bytes:
                raise ValueError('BPMN supera el límite de bytes')
            xml = xml.decode('utf-8')
        if not isinstance(xml, str):
            raise ValueError('Se requiere XML BPMN UTF-8')
        contenido = xml.encode('utf-8')
    except UnicodeError as exc:
        raise ValueError('Se requiere XML BPMN UTF-8') from exc
    if len(contenido) > max_bytes:
        raise ValueError('BPMN supera el límite de bytes')
    if '\x00' in xml or re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b', xml, re.IGNORECASE):
        raise ValueError('DTD y ENTITY no están permitidos en BPMN')
    if re.search(r'<\?(?!xml(?:\s|\?>))', xml):
        raise ValueError('Instrucciones XML de procesamiento no permitidas')
    try:
        raiz = ET.fromstring(contenido)
    except ET.ParseError as exc:
        raise ValueError('XML BPMN mal formado') from exc
    if raiz.tag != f'{{{MODEL}}}definitions':
        raise ValueError('La raíz debe ser definitions del namespace BPMN MODEL')
    if (raiz.get('exporter') or '').strip().upper() == 'SGC':
        raise ValueError('Los diagramas SGC generados no se pueden editar aquí')

    ids = {}
    referencias = []
    for elemento in raiz.iter():
        ns, local = _nombre(elemento.tag)
        if ns not in NAMESPACES:
            raise ValueError('Namespace de extensión no permitido en el editor manual')
        if local in {'extensionElements', 'scriptTask', 'script'}:
            raise ValueError('Scripts y extensiones no están permitidos en el editor manual')
        identidad = elemento.get('id')
        if identidad:
            if identidad in ids:
                raise ValueError(f'ID BPMN duplicado: {identidad}')
            ids[identidad] = elemento
        if ns == MODEL and local == 'sequenceFlow' and not all(elemento.get(k) for k in ('sourceRef', 'targetRef')):
            raise ValueError('sequenceFlow requiere sourceRef y targetRef')
        for atributo, valor in elemento.attrib.items():
            ans, nombre = _nombre(atributo)
            if ans and ans not in ATTRIBUTE_NAMESPACES:
                raise ValueError('Atributo de extensión no permitido')
            if nombre.lower().startswith('on') or nombre in {'scriptFormat', 'expressionLanguage'}:
                raise ValueError('Atributo ejecutable no permitido')
            if nombre == 'isExecutable' and valor not in {'false', '0'}:
                raise ValueError('El editor solo admite diagramas no ejecutables')
            if nombre == 'implementation' and valor not in {'##unspecified', ''}:
                raise ValueError('Implementación ejecutable no permitida')
            if nombre.endswith('Ref') or nombre in {'bpmnElement', 'default'}:
                referencias.append((elemento, nombre, valor))
        if ns == MODEL and (local in TEXT_REFS or local.endswith('Ref')):
            referencias.append((elemento, local, (elemento.text or '').strip()))

    for elemento, campo, referencia in referencias:
        destino = ids.get(referencia)
        if destino is None:
            raise ValueError(f'Referencia BPMN local inexistente: {referencia}')
        ns, local = _nombre(elemento.tag)
        dns, tipo = _nombre(destino.tag)
        if ns == MODEL and ((local == 'sequenceFlow' and campo in {'sourceRef', 'targetRef'}) or campo == 'flowNodeRef'):
            if dns != MODEL or tipo not in FLOW_NODES:
                raise ValueError(f'La referencia {referencia} no apunta a una actividad/evento/gateway')
        if campo in {'incoming', 'outgoing', 'default'} and (dns != MODEL or tipo != 'sequenceFlow'):
            raise ValueError(f'La referencia {referencia} no apunta a sequenceFlow')
    return contenido
