<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import SelectorBuscador from '@/components/ui/SelectorBuscador.vue'
import { useLinkSearch } from '@/composables/useLinkSearch'

const props = defineProps({
  modelValue: { type: String, default: null },
  doctype: { type: String, required: true },
  placeholder: { type: String, default: 'Buscar…' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])

const { search, query } = useLinkSearch(props.doctype)

// Al montar se busca UNA cosa: si ya hay valor, ese valor —para saber cómo se
// llama—; si no, el catálogo inicial.
//
// Antes se lanzaban las dos a la vez y ganaba la que respondiera la última.
// Cuando ganaba el catálogo, el valor guardado no estaba entre las opciones y el
// campo mostraba el código pelado: «S04» en vez de «Gestión tecnológica». Un
// código no le dice nada a quien abre el documento para revisarlo.
onMounted(() => query(props.modelValue || ''))

const options = computed(() =>
  (search.data || []).map((r) => ({
    label: r.label || r.value,
    value: r.value,
    description: r.description && r.description !== r.label ? r.description : undefined,
  })),
)

// La etiqueta del valor elegido, recordada. Sin esto, en cuanto se escribe otra
// búsqueda el valor guardado desaparece de las opciones y el campo vuelve a
// enseñar el código.
const etiquetaGuardada = ref(null)

watch(
  [options, () => props.modelValue],
  ([lista, valor]) => {
    if (!valor) {
      etiquetaGuardada.value = null
      return
    }
    const encontrada = lista.find((o) => o.value === valor)
    if (encontrada) etiquetaGuardada.value = encontrada
    else if (etiquetaGuardada.value?.value !== valor) {
      // Aún no se conoce su nombre: se pide, y mientras tanto se enseña el
      // código, que es mejor que dejar el campo en blanco.
      etiquetaGuardada.value = { label: valor, value: valor }
      query(valor)
    }
  },
  { immediate: true },
)

const optionsWithCurrent = computed(() => {
  const g = etiquetaGuardada.value
  if (!g || options.value.some((o) => o.value === g.value)) return options.value
  return [g, ...options.value]
})

function onQuery(txt) {
  query(txt)
}
</script>

<template>
  <SelectorBuscador
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
