// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const confirmation = vi.hoisted(() => ({
  loading: false,
  error: null,
  submit: vi.fn(),
}))

vi.mock('frappe-ui', () => ({
  Badge: { props: ['label'], template: '<span>{{ label }}</span>' },
  Button: {
    props: ['loading', 'disabled'],
    emits: ['click'],
    template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
  },
  ErrorMessage: { props: ['message'], template: '<p>{{ message }}</p>' },
  FormControl: {
    props: ['modelValue', 'label', 'options'],
    emits: ['update:modelValue'],
    template: '<label>{{ label }}<textarea v-if="label === \'Justificación\'" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" /></label>',
  },
  useCall: vi.fn(() => confirmation),
}))

import EstandarCard from './EstandarCard.vue'

const row = {
  name: 'VE-001',
  elemento_marco: 'EM-001',
  em_codigo: 'E1',
  em_denominacion: 'Propósitos articulados',
  nivel_propuesto: 'L',
  nivel_sigla: null,
  confirmado: 0,
  estado: 'Propuesto',
  justificacion: '',
}

describe('EstandarCard', () => {
  beforeEach(() => {
    confirmation.loading = false
    confirmation.error = null
    confirmation.submit.mockReset().mockResolvedValue({ ok: true, sigla: 'L' })
  })

  it('confirma el nivel mediante la acción de dominio sin editar estado ni confirmado', async () => {
    const wrapper = mount(EstandarCard, {
      props: { row, autoevaluacion: 'AE-001', canConfirm: true },
    })

    expect(wrapper.text()).toContain('Nivel propuesto')
    expect(wrapper.text()).toContain('L')
    expect(wrapper.text()).not.toContain('Confirmado por humano')
    expect(wrapper.text()).not.toContain('Guardar estándar')

    await wrapper.get('[data-test="nivel-sigla"]').setValue('LP')
    await wrapper.get('textarea').setValue('Indicadores revisados')
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(confirmation.submit).toHaveBeenCalledWith({
      autoevaluacion: 'AE-001',
      estandar: 'EM-001',
      nivel_sigla: 'LP',
      comentario: 'Indicadores revisados',
    })
    expect(wrapper.emitted('updated')).toHaveLength(1)
  })
})
