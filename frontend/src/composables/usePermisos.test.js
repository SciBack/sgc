// @vitest-environment jsdom

import { afterEach, describe, expect, it } from 'vitest'
import { puede, rolesUsuario, tieneRol } from './usePermisos'

afterEach(() => {
  delete window.permisos_ui
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
