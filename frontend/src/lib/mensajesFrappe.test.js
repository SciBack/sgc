import { describe, expect, it } from 'vitest'
import { esCancelacion, mensajeDeError, mensajesDelServidor } from './mensajesFrappe'

// Respuesta REAL de producción al crear un documento sin su campo obligatorio.
const faltaObligatorio = {
  exc_type: 'MandatoryError',
  exception: 'frappe.exceptions.MandatoryError: [Documento Controlado, TMP-ERR-001]: tipo_documento',
  _server_messages:
    '["{\\"message\\":\\"Error: falta el valor para Documento Controlado: Tipo de documento\\",\\"title\\":\\"Mensaje\\"}"]',
}

describe('el mensaje lo escribe Frappe', () => {
  it('lee el texto que manda el servidor, no uno propio', () => {
    // Frappe ya lo redacta, lo traduce y nombra el campo de forma legible.
    // Sustituirlo por un genérico dice menos y se desincroniza en cuanto el
    // servidor añade una validación nueva.
    expect(mensajeDeError(faltaObligatorio, 'No se pudo crear el registro.'))
      .toBe('Error: falta el valor para Documento Controlado: Tipo de documento')
  })

  it('limpia el HTML que Frappe mete en sus mensajes', () => {
    const err = { _server_messages: '["{\\"message\\":\\"Falta <b>Tipo</b><br>y algo más\\"}"]' }
    expect(mensajeDeError(err)).toBe('Falta Tipo y algo más')
  })

  it('junta varios mensajes cuando el servidor manda más de uno', () => {
    const err = {
      _server_messages: '["{\\"message\\":\\"Falta A\\"}", "{\\"message\\":\\"Falta B\\"}"]',
    }
    expect(mensajesDelServidor(err)).toEqual(['Falta A', 'Falta B'])
    expect(mensajeDeError(err)).toBe('Falta A · Falta B')
  })

  it('explica un 403 aunque venga sin mensaje', () => {
    expect(mensajeDeError({ exc_type: 'PermissionError' })).toMatch(/permiso/i)
  })

  it('solo cae al texto propio si el servidor no dijo nada', () => {
    expect(mensajeDeError({}, 'No se pudo guardar.')).toBe('No se pudo guardar.')
  })

  it('una cancelación no es un error y no se enseña', () => {
    const abortado = { message: 'signal is aborted without reason' }
    expect(esCancelacion(abortado)).toBe(true)
    expect(mensajeDeError(abortado, 'respaldo')).toBe('')
  })

  it('sin error no hay mensaje', () => {
    expect(mensajeDeError(null, 'respaldo')).toBe('')
  })
})
