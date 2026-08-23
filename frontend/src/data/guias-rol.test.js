import { describe, expect, it } from 'vitest'
import { GUIAS_ROL, indiceGuiaParaRoles } from './guias-rol'

describe('indiceGuiaParaRoles()', () => {
  it('a la DPGC le abre la suya, no la del Responsable de Programa', () => {
    // El fallo real: la pantalla abría siempre la primera guía, así que la
    // «guía según tu rol» le contaba a la DPGC el trabajo de otro.
    const i = indiceGuiaParaRoles(['DPGC', 'Desk User'])
    expect(GUIAS_ROL[i].rol).toBe('DPGC')
  })

  it('cubre los roles adyacentes de cada guía', () => {
    expect(GUIAS_ROL[indiceGuiaParaRoles(['Analista de Calidad (DPGC)'])].rol).toBe('DPGC')
    expect(GUIAS_ROL[indiceGuiaParaRoles(['Miembro de Comité de Calidad'])].rol).toBe(
      'Responsable de Calidad de Programa',
    )
  })

  it('con varios roles gana el más operativo', () => {
    const i = indiceGuiaParaRoles(['Auditor Interno', 'Responsable de Calidad de Programa'])
    expect(GUIAS_ROL[i].rol).toBe('Responsable de Calidad de Programa')
  })

  it('devuelve -1 para un rol sin guía propia (Rectorado, Data Steward...)', () => {
    // No hay guía para ellos todavía; la pantalla debe decirlo en vez de
    // mostrarles la de otro como si fuera la suya.
    expect(indiceGuiaParaRoles(['Rectorado/VR (lectura)'])).toBe(-1)
    expect(indiceGuiaParaRoles(['Data Steward'])).toBe(-1)
    expect(indiceGuiaParaRoles([])).toBe(-1)
  })
})
