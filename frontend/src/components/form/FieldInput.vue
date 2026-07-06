<script setup>
import { computed } from 'vue'
import { FormControl } from 'frappe-ui'
import LinkField from './LinkField.vue'

const props = defineProps({
  field: { type: Object, required: true }, // {fieldname, fieldtype, label, options, reqd}
  readOnly: { type: Boolean, default: false },
})

const value = defineModel({ default: null })

const TEXTAREA_TYPES = new Set(['Text', 'Small Text', 'Long Text', 'Text Editor', 'Code', 'Markdown Editor', 'HTML Editor', 'JSON'])
const NUMBER_TYPES = new Set(['Int', 'Float', 'Currency', 'Percent'])

const label = computed(() => props.field.label || props.field.fieldname)

const selectOptions = computed(() => {
  const raw = (props.field.options || '').split('\n').map((s) => s.trim())
  return raw.map((v) => ({ label: v || '—', value: v }))
})

// "Small Text" se ve como una sola línea en el prototipo del Desk, pero en la
// práctica siempre son párrafos cortos (alcance, justificación) — un textarea
// de pocas filas es más honesto que un <input> de una línea que los trunca.
function rowsFor(fieldtype) {
  return fieldtype === 'Small Text' ? 2 : 4
}
</script>

<template>
  <div v-if="field.fieldtype === 'Link'" class="space-y-1.5">
    <label class="block text-base text-ink-gray-5">{{ label }}</label>
    <LinkField
      v-model="value"
      :doctype="field.options"
      :placeholder="`Buscar ${label}…`"
      :disabled="readOnly"
    />
  </div>

  <div v-else-if="field.fieldtype === 'Dynamic Link'" class="space-y-1.5">
    <FormControl v-model="value" type="text" :label="label" :disabled="readOnly" />
    <p class="text-p-xs text-ink-gray-4">
      Enlace dinámico — el tipo de documento lo define otro campo. Si no es evidente, editar desde el Desk.
    </p>
  </div>

  <FormControl
    v-else-if="field.fieldtype === 'Select'"
    type="select"
    v-model="value"
    :label="label"
    :options="selectOptions"
    :disabled="readOnly"
  />

  <FormControl
    v-else-if="field.fieldtype === 'Check'"
    type="checkbox"
    :label="label"
    :model-value="Boolean(Number(value))"
    :disabled="readOnly"
    @update:model-value="value = $event ? 1 : 0"
  />

  <FormControl
    v-else-if="field.fieldtype === 'Date'"
    type="date"
    v-model="value"
    :label="label"
    :disabled="readOnly"
  />

  <FormControl
    v-else-if="field.fieldtype === 'Datetime'"
    type="datetime"
    v-model="value"
    :label="label"
    :disabled="readOnly"
  />

  <FormControl
    v-else-if="NUMBER_TYPES.has(field.fieldtype)"
    type="number"
    v-model="value"
    :label="label"
    :disabled="readOnly"
  />

  <div v-else-if="field.fieldtype === 'Table'" class="space-y-1.5">
    <label class="block text-base text-ink-gray-5">{{ label }}</label>
    <p class="rounded bg-surface-gray-1 px-2.5 py-1.5 text-p-sm text-ink-gray-6">
      {{ Array.isArray(value) ? `${value.length} fila(s)` : 'Sin filas' }} — editar la tabla completa en el Desk.
    </p>
  </div>

  <FormControl
    v-else-if="TEXTAREA_TYPES.has(field.fieldtype)"
    type="textarea"
    v-model="value"
    :label="label"
    :rows="rowsFor(field.fieldtype)"
    :disabled="readOnly"
  />

  <FormControl v-else type="text" v-model="value" :label="label" :disabled="readOnly" />
</template>
