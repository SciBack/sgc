// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { avisar, avisos, cerrarAviso } from './useAvisos'

afterEach(() => {
  avisos.splice(0, avisos.length)
  vi.useRealTimers()
})

describe('avisos', () => {
  it('apila un aviso con su tono y su detalle', () => {
    avisar('Documento creado', 'exito', { detalle: 'PRO-S04-001' })

    expect(avisos).toHaveLength(1)
    expect(avisos[0].mensaje).toBe('Documento creado')
    expect(avisos[0].tono).toBe('exito')
    expect(avisos[0].detalle).toBe('PRO-S04-001')
  })

  it('ignora un mensaje vacío', () => {
    // Un aviso en blanco es peor que ninguno: ocupa sitio y no dice nada.
    avisar('')
    expect(avisos).toHaveLength(0)
  })

  it('se va solo', () => {
    vi.useFakeTimers()
    avisar('Cambios guardados', 'exito')

    expect(avisos).toHaveLength(1)
    vi.advanceTimersByTime(4001)
    expect(avisos).toHaveLength(0)
  })

  it('un error dura más que un éxito: hay que leerlo', () => {
    vi.useFakeTimers()
    avisar('No se pudo guardar', 'error')

    vi.advanceTimersByTime(4001)
    expect(avisos).toHaveLength(1)
    vi.advanceTimersByTime(6000)
    expect(avisos).toHaveLength(0)
  })

  it('uno permanente espera a que lo cierren', () => {
    vi.useFakeTimers()
    const id = avisar('Atención', 'aviso', { permanente: true })

    vi.advanceTimersByTime(60000)
    expect(avisos).toHaveLength(1)
    cerrarAviso(id)
    expect(avisos).toHaveLength(0)
  })

  it('cerrar uno no se lleva a los demás', () => {
    const primero = avisar('Uno')
    avisar('Dos')

    cerrarAviso(primero)

    expect(avisos).toHaveLength(1)
    expect(avisos[0].mensaje).toBe('Dos')
  })
})
