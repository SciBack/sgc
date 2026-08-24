import { describe, expect, it } from 'vitest'
import { camposAConsultar, columnasDeMeta, filtrosDeMeta } from './useListaDeMeta'

// Meta REAL de «Proceso» en producción, recortado.
const proceso = {
  autoname: 'field:codigo',
  fields: [
    { fieldname: 'codigo', label: 'Código', fieldtype: 'Data', in_list_view: 1 },
    { fieldname: 'proceso', label: 'Proceso', fieldtype: 'Data', in_list_view: 1 },
    { fieldname: 'nivel', label: 'Nivel', fieldtype: 'Select', in_list_view: 1,
      in_standard_filter: 1, options: 'Estratégico\nClave\nSoporte' },
    { fieldname: 'estado', label: 'Estado', fieldtype: 'Select', in_standard_filter: 1,
      options: 'activo\ninactivo' },
    { fieldname: 'propietario_unidad', label: 'Unidad', fieldtype: 'Link', options: 'Unidad Organica' },
    { fieldname: 'lft', label: 'lft', fieldtype: 'Int', hidden: 1, in_list_view: 1 },
  ],
}

describe('columnas', () => {
  it('las declara el DocType, no la pantalla', () => {
    // Antes se pedían dos campos fijos —name y modified— para los 39 DocTypes,
    // así que en Proceso se veía «S04» y una fecha.
    expect(columnasDeMeta(proceso).map((c) => c.key)).toEqual(['codigo', 'proceso', 'nivel'])
  })

  it('no repite el nombre cuando el DocType se nombra por uno de sus campos', () => {
    // `autoname: field:codigo` -> el `name` ES el código: dos columnas gemelas.
    expect(columnasDeMeta(proceso).map((c) => c.key)).not.toContain('name')
  })

  it('añade el nombre cuando ninguna columna lo representa', () => {
    const otro = { autoname: 'hash', fields: [
      { fieldname: 'titulo', label: 'Título', in_list_view: 1 },
    ] }
    expect(columnasDeMeta(otro).map((c) => c.key)).toEqual(['name', 'titulo'])
  })

  it('ignora los campos ocultos', () => {
    expect(columnasDeMeta(proceso).map((c) => c.key)).not.toContain('lft')
  })

  it('si el DocType no declara ninguna, muestra al menos el registro', () => {
    expect(columnasDeMeta({ fields: [] }).map((c) => c.key)).toEqual(['name'])
  })
})

describe('filtros', () => {
  it('los declara el DocType', () => {
    expect(filtrosDeMeta(proceso).map((f) => f.key)).toEqual(['nivel', 'estado'])
  })

  it('un Select trae sus opciones ya listas', () => {
    const nivel = filtrosDeMeta(proceso).find((f) => f.key === 'nivel')
    expect(nivel.opciones).toEqual(['Estratégico', 'Clave', 'Soporte'])
  })

  it('un campo que no se filtra no aparece', () => {
    expect(filtrosDeMeta(proceso).map((f) => f.key)).not.toContain('propietario_unidad')
  })
})

describe('qué se le pide al servidor', () => {
  it('las columnas más name y modified, sin repetir', () => {
    const campos = camposAConsultar(columnasDeMeta(proceso))
    expect(campos).toContain('name')
    expect(campos).toContain('modified')
    expect(campos).toContain('codigo')
    expect(new Set(campos).size).toBe(campos.length)
  })
})
