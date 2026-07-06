<script setup>
import { reactive, ref } from 'vue'
import { Button, ErrorMessage, FormControl } from 'frappe-ui'
import { useDoctype } from 'frappe-ui'
import NivelSelect from './NivelSelect.vue'

const props = defineProps({
  row: { type: Object, required: true }, // Valoracion Estandar + em_*/nivel_* joins
})

const values = reactive({
  nivel: props.row.nivel,
  estado: props.row.estado,
  confirmado: props.row.confirmado,
  justificacion: props.row.justificacion,
})

const estadoOptions = [
  { label: 'Borrador', value: 'Borrador' },
  { label: 'Propuesto', value: 'Propuesto' },
  { label: 'Aprobado', value: 'Aprobado' },
]

const doctype = useDoctype('Valoracion Estandar')
const saved = ref(false)

async function save() {
  saved.value = false
  await doctype.setValue.submit({ name: props.row.name, ...values })
  saved.value = true
  setTimeout(() => (saved.value = false), 2000)
}
</script>

<template>
  <div class="rounded-lg border border-outline-gray-1 bg-surface-base p-4">
    <div class="mb-3 flex items-baseline gap-2">
      <span class="rounded bg-surface-gray-2 px-1.5 py-0.5 font-mono text-xs font-semibold text-ink-gray-6">
        {{ row.em_codigo }}
      </span>
      <h3 class="font-display text-base font-semibold text-ink-gray-9">{{ row.em_denominacion }}</h3>
    </div>

    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div>
        <label class="mb-1.5 block text-base text-ink-gray-5">Nivel (NL/L/LP)</label>
        <NivelSelect v-model="values.nivel" />
      </div>
      <FormControl type="select" label="Estado" v-model="values.estado" :options="estadoOptions" />
    </div>

    <FormControl class="mt-3" type="textarea" label="Justificación" v-model="values.justificacion" :rows="3" />

    <FormControl class="mt-3" type="checkbox" label="Confirmado por humano"
      :model-value="Boolean(Number(values.confirmado))"
      @update:model-value="values.confirmado = $event ? 1 : 0" />

    <div class="mt-3 flex items-center gap-3 border-t border-outline-gray-1 pt-3">
      <Button variant="outline" :loading="doctype.setValue.loading" @click="save">Guardar estándar</Button>
      <span v-if="saved" class="text-p-sm text-ink-green-6">Guardado.</span>
      <ErrorMessage v-if="doctype.setValue.error" :message="doctype.setValue.error.message" />
    </div>

    <div class="mt-4 space-y-2">
      <slot name="criterios" />
    </div>
  </div>
</template>
