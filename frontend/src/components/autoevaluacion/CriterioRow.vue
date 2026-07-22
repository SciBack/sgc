<script setup>
import { reactive, ref, watch } from 'vue'
import { Badge, Button, ErrorMessage, FormControl, useCall, useDoctype } from 'frappe-ui'

const props = defineProps({
  row: { type: Object, required: true }, // Valoracion Criterio + cr_* joins
})
const emit = defineEmits(['updated'])

const values = reactive({
  cumple: props.row.cumple,
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
const doctype = useDoctype('Valoracion Criterio')
const saved = ref(false)
const expanded = ref(false)

async function save() {
  saved.value = false
  await doctype.setValue.submit({ name: props.row.name, ...values })
  if (doctype.setValue.error) return
  saved.value = true
  emit('updated')
  setTimeout(() => (saved.value = false), 2000)
}

// Evidencias que respaldan este criterio (M09, vía Trazabilidad). Se cargan
// perezosamente al abrir el detalle — no en el listado, para no disparar una
// llamada por criterio al pintar la autoevaluación completa.
const evidencias = useCall({
  url: '/api/v2/method/sgc.sgc_nucleo.doctype.evidencia.evidencia.evidencias_de_elemento',
  immediate: false,
})
let evidenciasCargadas = false
watch(expanded, (open) => {
  if (open && !evidenciasCargadas && props.row.criterio) {
    evidenciasCargadas = true
    evidencias.submit({ elemento_marco: props.row.criterio })
  }
})

const estadoTheme = {
  Valida: 'green',
  Pendiente: 'gray',
  Observada: 'orange',
  Subsanada: 'blue',
  Vencida: 'red',
}
</script>

<template>
  <div class="rounded-xl border border-outline-gray-1 bg-surface-base p-4">
    <div class="flex flex-wrap items-center gap-3">
      <div class="min-w-0 flex-1">
        <span class="rounded-lg bg-marca-primaria-50 px-2 py-1 font-mono text-2xs font-semibold text-marca-primaria-700">
          {{ row.cr_codigo }}
        </span>
        <span class="ml-2 text-p-sm text-ink-gray-8">{{ row.cr_denominacion }}</span>
      </div>
      <FormControl type="select" variant="outline" v-model="values.cumple" :options="cumpleOptions" class="w-40" />
      <Badge :label="row.estado || 'Pendiente'" :theme="row.estado === 'Valorado' ? 'blue' : 'gray'" variant="subtle" size="sm" />
      <button
        type="button"
        class="text-p-xs text-ink-gray-5 hover:text-ink-gray-8 hover:underline"
        @click="expanded = !expanded"
      >
        {{ expanded ? 'ocultar detalle' : 'detalle' }}
      </button>
      <Button size="sm" variant="solid" class="sb-primary-action btn-press" :loading="doctype.setValue.loading" @click="save">Guardar</Button>
      <span v-if="saved" class="text-p-xs text-ink-green-6">Guardado.</span>
    </div>

    <div v-if="expanded" class="detalle mt-3 space-y-4 border-t border-outline-gray-1 pt-3">
      <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <FormControl type="textarea" variant="outline" label="Observación" v-model="values.observacion" :rows="2" />
        <FormControl type="textarea" variant="outline" label="Debilidad / OM" v-model="values.debilidad" :rows="2" />
        <FormControl type="textarea" variant="outline" label="Comentario (sustento)" v-model="values.comentario" :rows="2" />
      </div>

      <!-- Evidencias que sustentan el criterio -->
      <div>
        <div class="mb-1.5 flex items-center gap-2">
          <span class="text-p-xs font-semibold uppercase tracking-wide text-ink-gray-5">Evidencias</span>
          <span v-if="evidencias.data" class="text-2xs text-ink-gray-4">{{ evidencias.data.length }}</span>
        </div>

        <div v-if="evidencias.loading" class="text-p-xs text-ink-gray-4">Cargando…</div>
        <ul v-else-if="(evidencias.data || []).length" class="space-y-1">
          <li
            v-for="ev in evidencias.data"
            :key="ev.name"
            class="flex items-center gap-2 rounded border border-outline-gray-1 bg-surface-white px-2.5 py-1.5"
          >
            <span class="font-mono text-2xs font-semibold text-ink-gray-5">{{ ev.codigo }}</span>
            <span class="min-w-0 flex-1 truncate text-p-xs text-ink-gray-8" :title="ev.titulo">{{ ev.titulo }}</span>
            <Badge :label="ev.estado" :theme="estadoTheme[ev.estado] || 'gray'" variant="subtle" size="sm" />
            <a
              v-if="ev.archivo"
              :href="ev.archivo"
              target="_blank"
              rel="noopener"
              class="ev-open flex size-6 shrink-0 items-center justify-center rounded text-ink-gray-4 hover:bg-surface-gray-3 hover:text-ink-gray-7"
              title="Abrir archivo"
            >
              <span class="lucide-external-link size-3.5" aria-hidden="true" />
            </a>
          </li>
        </ul>
        <p v-else class="text-p-xs text-ink-gray-4">
          Sin evidencias vinculadas — cárgalas en el módulo Evidencias y vincúlalas a este criterio.
        </p>
      </div>
    </div>
    <ErrorMessage v-if="doctype.setValue.error" class="mt-2" :message="doctype.setValue.error.message" />
  </div>
</template>

<style scoped>
.detalle {
  transition: opacity 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
@starting-style {
  .detalle { opacity: 0; }
}
.ev-open {
  transition: background-color 150ms ease, color 150ms ease, transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.ev-open:active { transform: scale(0.92); }
@media (prefers-reduced-motion: reduce) {
  .detalle, .ev-open { transition-property: opacity, background-color, color; }
}
</style>
