"""Ingesta v1. Un bloqueo por fuente serializa lotes y adopción de datos heredados.

Sin commits internos: POST Frappe confirma el lote completo. Rechazos de negocio
se devuelven como resultado Rechazado para que su registro sobreviva al commit.
Errores inesperados se propagan y revierten la transacción completa.
"""
import json
from contextlib import contextmanager
from contextvars import ContextVar

import frappe
from frappe.utils import now_datetime

from sgc.ingesta_contrato import (
    ErrorContrato,
    clave_medicion,
    evaluar_reglas,
    huella,
    instante,
    normalizar_lote,
)

_ESCRITURA = ContextVar('sgc_ingesta', default=False)


def en_ingesta():
    return _ESCRITURA.get()


@contextmanager
def _escritura():
    token = _ESCRITURA.set(True)
    try:
        yield
    finally:
        _ESCRITURA.reset(token)


def _autorizar(nombre):
    if frappe.session.user == 'Guest':
        frappe.throw('Autenticación requerida', frappe.PermissionError)
    # Mismo orden de bloqueo en todas las publicaciones: no hay carrera de primer insert.
    q = frappe.qb.DocType('Fuente Dato')
    existe = frappe.qb.from_(q).select(q.name).where(q.name == nombre).for_update().run()
    if not existe:
        frappe.throw('Fuente no autorizada', frappe.PermissionError)
    fuente = frappe.get_doc('Fuente Dato', nombre)
    if fuente.usuario_ingesta != frappe.session.user or fuente.estado != 'Activa':
        frappe.throw('La cuenta no está autorizada para esta fuente activa', frappe.PermissionError)
    if not (fuente.codigo_publicacion or '').strip():
        frappe.throw('Configure el código de publicación de la fuente')
    if not frappe.has_permission('Valor Indicador', ptype='create'):
        frappe.throw('La cuenta no puede crear mediciones', frappe.PermissionError)
    return fuente


def _autorizar_con_reintento(nombre):
    # PostgreSQL/Frappe usa REPEATABLE READ: esperar FOR UPDATE puede producir
    # 40001 si el ganador actualizó ultima_carga. Renovar el snapshot únicamente
    # antes de cualquier escritura; nunca revertir trabajo previo del llamador.
    for intento in range(3):
        try:
            return _autorizar(nombre)
        except Exception as exc:
            if (getattr(exc, 'pgcode', None) != '40001' or intento == 2
                    or getattr(frappe.db, 'transaction_writes', None) != 0):
                raise
            frappe.db.rollback()


def _reglas(fuente, indicador):
    filas = frappe.get_all('Regla Validacion', filters={'activa': 1}, fields=[
        'name', 'fuente_dato', 'indicador', 'tipo_regla', 'campo_objetivo',
        'valor_min', 'valor_max', 'severidad', 'mensaje', 'expresion'])
    return [r for r in filas if (r.fuente_dato or r.indicador)
            and (not r.fuente_dato or r.fuente_dato == fuente)
            and (not r.indicador or r.indicador == indicador)]


def _existente(fuente, fila):
    identidad = clave_medicion(fuente.name, fila)
    nombre = frappe.db.get_value('Valor Indicador', {'ingesta_clave': identidad}, 'name')
    if nombre:
        return nombre
    # Adopción explícita: mismo grano completo, incluyendo ambos ámbitos vacíos.
    v = frappe.qb.DocType('Valor Indicador')
    from frappe.query_builder.functions import Coalesce
    encontrados = (frappe.qb.from_(v).select(v.name).where(
        (v.fuente == fuente.codigo_publicacion) & (v.indicador == fila['indicador'])
        & (v.periodo_academico == fila['periodo_academico'])
        & (Coalesce(v.programa_sede, '') == (fila.get('programa_sede') or ''))
        & (Coalesce(v.unidad_organica, '') == (fila.get('unidad_organica') or ''))
    ).for_update().run())
    if len(encontrados) > 1:
        raise ErrorContrato('Hay mediciones heredadas duplicadas; reconciliar antes de publicar')
    return encontrados[0][0] if encontrados else None


def _prevalidar(fuente, datos):
    preparados, errores = [], []
    for fila in datos['mediciones']:
        try:
            for campo, dt in [('indicador', 'Indicador'), ('periodo_academico', 'Periodo Academico'),
                              ('programa_sede', 'Programa Sede'), ('unidad_organica', 'Unidad Organica')]:
                if fila.get(campo) and not frappe.db.exists(dt, fila[campo]):
                    raise ErrorContrato(f'{campo}: referencia inexistente')
            if frappe.db.get_value('Periodo Academico', fila['periodo_academico'], 'estado') != 'abierto':
                raise ErrorContrato('Período cerrado')
            # El servicio escribe con privilegios internos después del preflight;
            # comprobar aquí permisos del documento y de todos sus Links.
            if fila.get('programa_sede'):
                from sgc.permissions import programas_permitidos
                permitidos = programas_permitidos()
                if permitidos is not None and fila['programa_sede'] not in permitidos:
                    raise ErrorContrato('Programa fuera del ámbito autorizado')
            avisos = evaluar_reglas(fila, _reglas(fuente.name, fila['indicador']))
            if any(a['severidad'] == 'Bloqueante' for a in avisos):
                raise ErrorContrato('; '.join(a['mensaje'] for a in avisos if a['severidad'] == 'Bloqueante'))
            nombre = _existente(fuente, fila)
            candidato = frappe.get_doc('Valor Indicador', nombre) if nombre else frappe.new_doc('Valor Indicador')
            if nombre and not frappe.has_permission('Valor Indicador', ptype='write', doc=candidato):
                raise ErrorContrato('Medición vigente fuera del ámbito autorizado')
            candidato.update({k: fila.get(k) for k in ('indicador', 'periodo_academico', 'programa_sede', 'unidad_organica')})
            candidato.fuente_dato = fuente.name
            if not frappe.has_permission('Valor Indicador', ptype='write' if nombre else 'create', doc=candidato):
                raise ErrorContrato('Referencias fuera del ámbito autorizado')
            if nombre:
                anterior = frappe.db.get_value('Valor Indicador', nombre, 'corte_fin')
                if anterior and instante(fila['corte_fin']) < instante(anterior):
                    raise ErrorContrato('El corte es anterior a la medición vigente')
            preparados.append((fila, nombre, avisos))
        except ErrorContrato as exc:
            errores.append({'indicador': fila['indicador'], 'codigo': 'MEDICION_RECHAZADA', 'mensaje': str(exc)})
    return preparados, errores


@frappe.whitelist(methods=['POST'])
def publicar_lote(lote):
    try:
        datos = normalizar_lote(lote)
    except ErrorContrato as exc:
        frappe.throw(str(exc))
    fuente = _autorizar_con_reintento(datos['fuente_dato'])
    nombre_lote = huella([fuente.name, datos['run_id']])
    fingerprint = huella(datos)
    if frappe.db.exists('Lote Ingesta', nombre_lote):
        previo = frappe.get_doc('Lote Ingesta', nombre_lote)
        if previo.hash_contenido != fingerprint:
            frappe.throw('El run_id ya se utilizó con otro contenido')
        return json.loads(previo.respuesta)
    preparados, errores = _prevalidar(fuente, datos)
    resultado = {'lote': nombre_lote, 'estado': 'Rechazado' if errores else 'Aceptado',
                 'mediciones': [], 'advertencias': [], 'errores': errores}
    with _escritura():
        # Se inserta antes para que los Links de las mediciones sean válidos.
        registro = frappe.get_doc({'doctype': 'Lote Ingesta', 'name': nombre_lote,
            'fuente_dato': fuente.name, 'run_id': datos['run_id'], 'hash_contenido': fingerprint,
            'extraido_en': datos['extraido_en'], 'estado': resultado['estado'],
            'respuesta': json.dumps(resultado, ensure_ascii=False)}).insert(ignore_permissions=True)
        if not errores:
            for fila, nombre, avisos in preparados:
                vi = frappe.get_doc('Valor Indicador', nombre) if nombre else frappe.new_doc('Valor Indicador')
                for campo in ('indicador', 'periodo_academico', 'programa_sede', 'unidad_organica',
                              'valor_num', 'cobertura_pct', 'formula_version', 'corte_inicio', 'corte_fin', 'estado_medicion'):
                    vi.set(campo, fila.get(campo))
                vi.fuente = fuente.codigo_publicacion
                vi.fuente_dato = fuente.name
                vi.ingesta_clave = clave_medicion(fuente.name, fila)
                vi.lote_ingesta = registro.name
                vi.datos_ingesta = json.dumps(fila, ensure_ascii=False, sort_keys=True)
                vi.unidad_medicion = fila['unidad']
                vi.fecha = now_datetime()
                vi.calculado = 1
                vi.registrado_por = frappe.session.user
                # No sobrescribir prosa histórica: los consumidores migran a datos_ingesta.
                vi.save(ignore_permissions=True)
                resultado['mediciones'].append(vi.name)
                for aviso in avisos:
                    frappe.get_doc({'doctype': 'Alerta Indicador', 'indicador': vi.indicador,
                        'valor_indicador': vi.name, 'tipo': 'Validación fallida', 'severidad': 'Media',
                        'periodo_academico': vi.periodo_academico, 'programa_sede': vi.programa_sede,
                        'unidad_organica': vi.unidad_organica, 'valor_medido': vi.valor_num,
                        'mensaje': aviso['mensaje'], 'responsable': fuente.responsable,
                        'estado': 'Abierta'}).insert(ignore_permissions=True)
                    resultado['advertencias'].append({'indicador': vi.indicador, **aviso})
            frappe.db.set_value('Fuente Dato', fuente.name, 'ultima_carga', now_datetime())
        registro.respuesta = json.dumps(resultado, ensure_ascii=False)
        registro.save(ignore_permissions=True)
    return resultado
