<script setup>
import { computed, onMounted, watch } from 'vue'
import { Combobox } from 'frappe-ui'
import { useLinkSearch } from '@/composables/useLinkSearch'

const props = defineProps({
  modelValue: { type: String, default: null },
  doctype: { type: String, required: true },
  placeholder: { type: String, default: 'Buscar…' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const { search, query } = useLinkSearch(props.doctype)

// Primera carga: trae un listado inicial y, si ya hay un valor guardado, una
// búsqueda dirigida a ese valor para que se muestre con su etiqueta real (no
// solo el código interno) sin esperar a que el usuario escriba.
onMounted(() => {
  query('')
  if (props.modelValue) query(props.modelValue)
})

const options = computed(() =>
  (search.data || []).map((r) => ({
    label: r.label || r.value,
    value: r.value,
    description: r.description && r.description !== r.label ? r.description : undefined,
  })),
)

// Si el valor ya viene seteado pero aún no aparece en las opciones (p.ej. al
// entrar directo al formulario), lo agregamos igual para que el Combobox
// muestre algo con sentido en vez de dejarlo en blanco.
const optionsWithCurrent = computed(() => {
  if (!props.modelValue || options.value.some((o) => o.value === props.modelValue)) {
    return options.value
  }
  return [{ label: props.modelValue, value: props.modelValue }, ...options.value]
})

function onQuery(txt) {
  query(txt)
}
</script>

<template>
  <Combobox
    :model-value="modelValue"
    :options="optionsWithCurrent"
    :loading="search.loading"
    :placeholder="placeholder"
    :disabled="disabled"
    class="w-full"
    @update:model-value="emit('update:modelValue', $event)"
    @update:query="onQuery"
  />
</template>
