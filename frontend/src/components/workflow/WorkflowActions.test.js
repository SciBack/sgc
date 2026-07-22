// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  transitions: {
    data: [{ action: 'Iniciar evaluacion', next_state: 'En curso' }],
    loading: false,
    error: null,
    submit: vi.fn(),
  },
  apply: {
    data: null,
    loading: false,
    error: null,
    submit: vi.fn(),
  },
}))

vi.mock('frappe-ui', () => ({
  Button: {
    props: ['loading', 'disabled', 'variant'],
    emits: ['click'],
    template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
  },
  ErrorMessage: {
    props: ['message'],
    template: '<p data-test="error">{{ message }}</p>',
  },
  useCall: vi.fn((options) =>
    options.url.includes('get_transitions') ? api.transitions : api.apply,
  ),
}))

import WorkflowActions from './WorkflowActions.vue'

const document = {
  doctype: 'Autoevaluacion',
  name: 'AE-TEST-001',
  estado: 'Planificada',
  docstatus: 0,
}

describe('WorkflowActions', () => {
  beforeEach(() => {
    api.transitions.data = [{ action: 'Iniciar evaluacion', next_state: 'En curso' }]
    api.transitions.loading = false
    api.transitions.error = null
    api.transitions.submit.mockReset().mockResolvedValue(api.transitions.data)
    api.apply.loading = false
    api.apply.error = null
    api.apply.submit.mockReset().mockResolvedValue({ ...document, estado: 'En curso' })
  })

  it('consulta y ejecuta solo las transiciones autorizadas por Frappe', async () => {
    const wrapper = mount(WorkflowActions, { props: { document } })
    await flushPromises()

    expect(api.transitions.submit).toHaveBeenCalledWith({ doc: JSON.stringify(document) })
    expect(wrapper.text()).toContain('Planificada')
    expect(wrapper.text()).toContain('Iniciar evaluación')

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(api.apply.submit).toHaveBeenCalledWith({
      doc: JSON.stringify(document),
      action: 'Iniciar evaluacion',
    })
    expect(wrapper.emitted('completed')?.[0]?.[0]).toMatchObject({ estado: 'En curso' })
  })

  it('explica cuando el rol no tiene acciones para el estado actual', async () => {
    api.transitions.data = []
    const wrapper = mount(WorkflowActions, { props: { document } })
    await flushPromises()

    expect(wrapper.text()).toContain('No hay acciones disponibles para tu rol en este estado')
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('muestra el error del servidor sin anunciar una transición exitosa', async () => {
    api.apply.error = { message: 'Self approval is not allowed' }
    api.apply.submit.mockResolvedValue(null)
    const wrapper = mount(WorkflowActions, { props: { document } })
    await flushPromises()

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-test="error"]').text()).toContain('Self approval is not allowed')
    expect(wrapper.emitted('completed')).toBeUndefined()
  })
})
