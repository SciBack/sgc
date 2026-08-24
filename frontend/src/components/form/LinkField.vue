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
// El catálogo inicial, para que el desplegable tenga qué mostrar al abrirse.
// La etiqueta del valor guardado NO depende de esto: tiene su propia llamada.
onMounted(() => query(''))

const options = computed(() =>
  (search.data || []).map((r) => ({
    label: r.label || r.value,
    value: r.value,
    description: r.description && r.description !== r.label ? r.description : undefined,
  })),
)

// La etiqueta del valor elegido se resuelve con su PROPIA llamada y se recuerda.
//
// Depender de la lista de búsqueda no funciona: esa lista cambia con cada tecla,
// y en cuanto se escribe otra cosa el valor elegido desaparece de ella. El campo
// volvía entonces a enseñar el código —«S04» en vez de «Gestión tecnológica»—,
// que no le dice nada a quien abre el documento para revisarlo.
const etiquetaGuardada = ref(null)

async function resolverEtiqueta(valor) {
  if (!valor) {
    etiquetaGuardada.value = null
    return
  }
  if (etiquetaGuardada.value?.value === valor && etiquetaGuardada.value.label !== valor) return

  // Mientras se resuelve se enseña el código: peor sería dejarlo en blanco.
  etiquetaGuardada.value = { label: valor, value: valor }
  try {
    const res = await fetch('/api/v2/method/frappe.desk.search.search_link', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': window.csrf_token },
      body: JSON.stringify({ doctype: props.doctype, txt: valor }),
    })
    if (!res.ok) return
    const cuerpo = await res.json()
    const fila = (cuerpo.data || cuerpo.message || []).find((r) => r.value === valor)
    if (fila?.label && fila.label !== valor) {
      etiquetaGuardada.value = { label: fila.label, value: valor, description: fila.description }
    }
  } catch {
    /* se queda el código */
  }
}

watch(() => props.modelValue, resolverEtiqueta, { immediate: true })

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
