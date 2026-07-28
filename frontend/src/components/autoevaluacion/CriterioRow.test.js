// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const setValue = vi.hoisted(() => ({ loading: false, error: null, submit: vi.fn() }))

// Solo se simulan los hooks de datos: los componentes visuales ya son los de la
// casa (@/components/ui) y se montan de verdad.
vi.mock('frappe-ui', () => ({
  useCall: vi.fn(() => ({ data: [], loading: false, error: null, submit: vi.fn() })),
  useDoctype: vi.fn(() => ({ setValue })),
}))

import CriterioRow from './CriterioRow.vue'

const row = {
  name: 'VC-001',
  criterio: 'CR-001',
  cr_codigo: 'C1',
  cr_denominacion: 'Criterio de prueba',
  cumple: 'Cumple parcial',
  estado: 'Valorado',
  observacion: '',
  debilidad: '',
  comentario: '',
}

describe('CriterioRow', () => {
  beforeEach(() => setValue.submit.mockReset().mockResolvedValue({}))

  it('guarda el juicio sin permitir que el navegador escriba el estado', async () => {
    const wrapper = mount(CriterioRow, { props: { row } })

    expect(wrapper.findAll('select')).toHaveLength(1)
    expect(wrapper.text()).toContain('Valorado')

    await wrapper.get('button:last-of-type').trigger('click')

    expect(setValue.submit).toHaveBeenCalledOnce()
    expect(setValue.submit.mock.calls[0][0]).not.toHaveProperty('estado')
  })
})
