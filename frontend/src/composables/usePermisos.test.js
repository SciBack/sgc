// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import { doctypesDeTrabajo, puede, rolesUsuario, tieneFlujo, tieneRol } from './usePermisos'

afterEach(() => {
  delete window.permisos_ui
  delete window.doctypes_trabajo
  delete window.doctypes_con_flujo
  delete window.user_roles
})

describe('puede()', () => {
  it('sin mapa de permisos no oculta nada (modo dev, sin boot)', () => {
    expect(puede('Evidencia', 'create')).toBe(true)
  })

  it('respeta el permiso del mapa', () => {
    window.permisos_ui = {
      Evidencia: { read: true, create: false, write: false, delete: false },
    }
    expect(puede('Evidencia', 'read')).toBe(true)
    expect(puede('Evidencia', 'create')).toBe(false)
    expect(puede('Evidencia', 'write')).toBe(false)
  })

  it('un DocType ausente del mapa se permite: ausencia no es denegación', () => {
    // Si un DocType nuevo no se lista, debe seguir apareciendo y que decida el
    // backend. Un botón que desaparece por olvido no da ningún mensaje de error.
    window.permisos_ui = { Evidencia: { read: true, create: true } }
    expect(puede('File', 'create')).toBe(true)
    expect(puede('Doctype Que No Existe', 'read')).toBe(true)
  })
})

describe('roles', () => {
  it('lee los roles del boot', () => {
    window.user_roles = ['DPGC', 'Desk User']
    expect(rolesUsuario()).toContain('DPGC')
    expect(tieneRol('DPGC')).toBe(true)
    expect(tieneRol('Auditor Interno')).toBe(false)
  })

  it('sin boot devuelve lista vacía', () => {
    expect(rolesUsuario()).toEqual([])
  })
})

describe('lo que cada persona trabaja', () => {
  it('lee del boot los doctypes que ejecuta', () => {
    window.doctypes_trabajo = ['Documento Controlado', 'Evidencia', 'Riesgo']
    expect(doctypesDeTrabajo()).toHaveLength(3)
    expect(doctypesDeTrabajo()).toContain('Documento Controlado')
  })

  it('sin boot devuelve lista vacía, y eso significa «no sé»', () => {
    // En dev no hay boot. Una lista vacía NO puede interpretarse como «esta
    // persona no trabaja nada», o el menú se quedaría en blanco.
    expect(doctypesDeTrabajo()).toEqual([])
  })

  it('trabajar no es lo mismo que poder leer', () => {
    // El caso medido en producción: el Dueño de Proceso LEE casi todo y solo
    // EJECUTA cuatro cosas. Son dos preguntas distintas y el menú usa las dos.
    window.permisos_ui = {
      'Documento Controlado': { read: true, write: true },
      'Marco Normativo': { read: true, write: false },
    }
    window.doctypes_trabajo = ['Documento Controlado']

    expect(puede('Marco Normativo', 'read')).toBe(true)
    expect(doctypesDeTrabajo()).not.toContain('Marco Normativo')
  })
})

describe('documentos con ciclo de vida', () => {
  it('reconoce los que llevan workflow', () => {
    window.doctypes_con_flujo = ['Documento Controlado', 'Evidencia']
    expect(tieneFlujo('Documento Controlado')).toBe(true)
    expect(tieneFlujo('Marco Normativo')).toBe(false)
  })

  it('sin boot no pinta acciones', () => {
    // Al revés que `puede`: aquí ante la duda se OCULTA. Pintar «Aprobar» donde
    // no hay flujo ofrece algo que va a fallar; no pintarlo solo omite.
    expect(tieneFlujo('Documento Controlado')).toBe(false)
  })
})
