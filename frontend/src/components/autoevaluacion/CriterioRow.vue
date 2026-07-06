<script setup>
import { reactive, ref } from 'vue'
import { Button, ErrorMessage, FormControl } from 'frappe-ui'
import { useDoctype } from 'frappe-ui'

const props = defineProps({
  row: { type: Object, required: true }, // Valoracion Criterio + cr_* joins
})

const values = reactive({
  cumple: props.row.cumple,
  estado: props.row.estado,
  observacion: props.row.observacion,
  debilidad: props.row.debilidad,
  comentario: props.row.comentario,
})

const cumpleOptions = [
  { label: 'Cumple', value: 'Cumple' },
  { label: 'Cumple parcial', value: 'Cumple parcial' },
  { label: 'No cumple', value: 'No cumple' },
  { label: 'No aplica', value: 'No aplica' },
]
const estadoOptions = [
  { label: 'Pendiente', value: 'Pendiente' },
  { label: 'En análisis', value: 'En analisis' },
  { label: 'Valorado', value: 'Valorado' },
  { label: 'Revisado', value: 'Revisado' },
]

const doctype = useDoctype('Valoracion Criterio')
const saved = ref(false)
const expanded = ref(false)

async function save() {
  saved.value = false
  await doctype.setValue.submit({ name: props.row.name, ...values })
  saved.value = true
  setTimeout(() => (saved.value = false), 2000)
}
</script>

<template>
  <div class="rounded-md border border-outline-gray-1 p-3">
    <div class="flex flex-wrap items-center gap-3">
      <div class="min-w-0 flex-1">
        <span class="rounded bg-surface-gray-2 px-1.5 py-0.5 font-mono text-2xs font-semibold text-ink-gray-6">
          {{ row.cr_codigo }}
        </span>
        <span class="ml-2 text-p-sm text-ink-gray-8">{{ row.cr_denominacion }}</span>
      </div>
      <FormControl type="select" v-model="values.cumple" :options="cumpleOptions" class="w-40" />
      <FormControl type="select" v-model="values.estado" :options="estadoOptions" class="w-36" />
      <button
        type="button"
        class="text-p-xs text-ink-gray-5 hover:text-ink-gray-8 hover:underline"
        @click="expanded = !expanded"
      >
        {{ expanded ? 'ocultar detalle' : 'detalle' }}
      </button>
      <Button size="sm" variant="outline" :loading="doctype.setValue.loading" @click="save">Guardar</Button>
      <span v-if="saved" class="text-p-xs text-ink-green-6">Guardado.</span>
    </div>

    <div v-if="expanded" class="mt-3 grid grid-cols-1 gap-3 border-t border-outline-gray-1 pt-3 sm:grid-cols-3">
      <FormControl type="textarea" label="Observación" v-model="values.observacion" :rows="2" />
      <FormControl type="textarea" label="Debilidad / OM" v-model="values.debilidad" :rows="2" />
      <FormControl type="textarea" label="Comentario (sustento)" v-model="values.comentario" :rows="2" />
    </div>
    <ErrorMessage v-if="doctype.setValue.error" class="mt-2" :message="doctype.setValue.error.message" />
  </div>
</template>
