"""Contrato de ingesta v1, puro: no importa Frappe ni ejecuta expresiones del usuario."""

import hashlib
import json
import math
from datetime import UTC, datetime, timezone

MAX_MEDICIONES = 500
MAX_BYTES = 1_000_000
CAMPOS = frozenset({
    'indicador', 'periodo_academico', 'programa_sede', 'unidad_organica', 'valor_num',
    'unidad', 'formula_version', 'corte_inicio', 'corte_fin', 'numerador', 'denominador',
    'cobertura_pct', 'meta_valor', 'meta_operador', 'meta_unidad', 'estado_medicion',
})


class ErrorContrato(ValueError):
    """Datos que no se pueden publicar sin inventar una interpretación."""


def _texto(valor, campo, maximo=140):
    if not isinstance(valor, str) or not valor.strip() or len(valor) > maximo:
        raise ErrorContrato(f'{campo}: texto requerido de hasta {maximo} caracteres')
    return valor.strip()


def _numero(valor, campo):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErrorContrato(f'{campo}: número requerido')
    if not math.isfinite(valor):
        raise ErrorContrato(f'{campo}: el número debe ser finito')
    return float(valor)


def instante(valor):
    if not isinstance(valor, str):
        raise ErrorContrato('Fecha ISO 8601 con zona horaria requerida')
    try:
        d = datetime.fromisoformat(valor.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ErrorContrato('Fecha ISO 8601 inválida') from exc
    if d.tzinfo is None:
        raise ErrorContrato('Fecha sin zona horaria')
    return d.astimezone(UTC)


def huella(objeto):
    texto = json.dumps(objeto, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(texto.encode()).hexdigest()


def clave_medicion(fuente, fila):
    return huella([fuente, fila['indicador'], fila['periodo_academico'],
                   fila.get('programa_sede') or '', fila.get('unidad_organica') or ''])


def normalizar_lote(datos):
    if isinstance(datos, str):
        if len(datos.encode()) > MAX_BYTES:
            raise ErrorContrato('Lote demasiado grande')
        try:
            datos = json.loads(datos)
        except ValueError as exc:
            raise ErrorContrato('JSON inválido') from exc
    if not isinstance(datos, dict) or set(datos) != {'version', 'fuente_dato', 'run_id', 'extraido_en', 'mediciones'}:
        raise ErrorContrato('Campos de lote inválidos')
    if type(datos['version']) is not int or datos['version'] != 1:
        raise ErrorContrato('Versión de contrato no soportada')
    if len(json.dumps(datos, ensure_ascii=False).encode()) > MAX_BYTES:
        raise ErrorContrato('Lote demasiado grande')
    filas = datos['mediciones']
    if not isinstance(filas, list) or not 1 <= len(filas) <= MAX_MEDICIONES:
        raise ErrorContrato(f'El lote requiere entre 1 y {MAX_MEDICIONES} mediciones')
    salida = {
        'version': 1, 'fuente_dato': _texto(datos['fuente_dato'], 'fuente_dato'),
        'run_id': _texto(datos['run_id'], 'run_id'),
        'extraido_en': instante(datos['extraido_en']).isoformat(), 'mediciones': [],
    }
    vistos = set()
    for fila in filas:
        if not isinstance(fila, dict) or set(fila) - CAMPOS:
            raise ErrorContrato('Campos de medición desconocidos')
        m = {k: _texto(fila.get(k), k) for k in
             ('indicador', 'periodo_academico', 'unidad', 'formula_version', 'estado_medicion')}
        if m['estado_medicion'] not in ('Provisional', 'Validado'):
            raise ErrorContrato('Estado de medición inválido')
        for campo in ('programa_sede', 'unidad_organica'):
            m[campo] = _texto(fila[campo], campo) if fila.get(campo) else None
        if m['programa_sede'] and m['unidad_organica']:
            raise ErrorContrato('La medición no puede tener dos ámbitos')
        m['valor_num'] = _numero(fila.get('valor_num'), 'valor_num')
        for campo in ('numerador', 'denominador', 'cobertura_pct', 'meta_valor'):
            v = fila.get(campo)
            m[campo] = _numero(v, campo) if v is not None else None
        if (m['numerador'] is None) != (m['denominador'] is None):
            raise ErrorContrato('Numerador y denominador deben declararse juntos')
        if m['denominador'] is not None and m['denominador'] <= 0:
            raise ErrorContrato('Denominador debe ser mayor que cero')
        if m['cobertura_pct'] is not None and not 0 <= m['cobertura_pct'] <= 100:
            raise ErrorContrato('Cobertura fuera de 0 a 100')
        for campo in ('corte_inicio', 'corte_fin'):
            m[campo] = instante(fila.get(campo)).isoformat()
        if not instante(m['corte_inicio']) <= instante(m['corte_fin']) <= instante(salida['extraido_en']):
            raise ErrorContrato('Orden temporal inválido: inicio <= fin <= extracción')
        for campo in ('meta_operador', 'meta_unidad'):
            m[campo] = fila.get(campo)
        if m['meta_valor'] is not None:
            if m['meta_operador'] not in ('>', '>=', '<', '<=', '='):
                raise ErrorContrato('Operador de meta inválido')
            m['meta_unidad'] = _texto(m['meta_unidad'], 'meta_unidad')
        elif m['meta_operador'] is not None or m['meta_unidad'] is not None:
            raise ErrorContrato('Meta incompleta')
        identidad = clave_medicion(salida['fuente_dato'], m)
        if identidad in vistos:
            raise ErrorContrato('Medición duplicada dentro del lote')
        vistos.add(identidad)
        salida['mediciones'].append(m)
    salida['mediciones'].sort(key=lambda f: clave_medicion(salida['fuente_dato'], f))
    return salida


def evaluar_reglas(fila, reglas):
    resultados = []
    for regla in reglas:
        tipo = regla.get('tipo_regla')
        campo = regla.get('campo_objetivo') or 'valor_num'
        if campo not in CAMPOS:
            raise ErrorContrato(f'Campo de regla no soportado: {campo}')
        valor = fila.get(campo)
        if tipo == 'Obligatorio':
            valida = valor is not None and valor != ''
        elif tipo == 'Rango':
            minimo, maximo = regla.get('valor_min'), regla.get('valor_max')
            if minimo is None and maximo is None:
                raise ErrorContrato('Regla de rango sin límites')
            valida = isinstance(valor, (int, float)) and not isinstance(valor, bool)
            valida = valida and (minimo is None or valor >= minimo) and (maximo is None or valor <= maximo)
        else:
            raise ErrorContrato(f'Tipo de regla no soportado por ingesta v1: {tipo}')
        if not valida:
            resultados.append({'regla': regla.get('name'), 'campo': campo,
                               'severidad': regla.get('severidad') or 'Bloqueante',
                               'mensaje': regla.get('mensaje') or 'Validación fallida'})
    return resultados
