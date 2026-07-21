<script setup>
import { computed } from 'vue'
import { Button, ErrorMessage, LoadingText, ScrollArea, useCall, useDoc } from 'frappe-ui'
import EstandarCard from '@/components/autoevaluacion/EstandarCard.vue'
import CriterioRow from '@/components/autoevaluacion/CriterioRow.vue'

const props = defineProps({ name: { type: String, required: true } })

const PRINT_FORMAT = 'Informe de Autoevaluacion SINEACE'

const doc = useDoc({ doctype: 'Autoevaluacion', name: props.name })

const estandares = useCall({
  url: '/api/v2/method/frappe.client.get_list',
  params: () => ({
    doctype: 'Valoracion Estandar',
    filters: JSON.stringify({ autoevaluacion: props.name }),
    fields: JSON.stringify([
      'name', 'elemento_marco', 'nivel', 'estado', 'confirmado', 'justificacion',
      'elemento_marco.codigo as em_codigo',
      'elemento_marco.denominacion as em_denominacion',
    ]),
    limit_page_length: 200,
  }),
  cacheKey: ['valoracion-estandar', props.name],
})

const criterios = useCall({
  url: '/api/v2/method/frappe.client.get_list',
  params: () => ({
    doctype: 'Valoracion Criterio',
    filters: JSON.stringify({ autoevaluacion: props.name }),
    fields: JSON.stringify([
      'name', 'criterio', 'cumple', 'estado', 'observacion', 'debilidad', 'comentario',
      'criterio.codigo as cr_codigo',
      'criterio.denominacion as cr_denominacion',
      'criterio.parent_elemento_marco as cr_padre',
    ]),
    limit_page_length: 500,
  }),
  cacheKey: ['valoracion-criterio', props.name],
})

// Orden natural E1, E2, …, E10 (no alfabético: "E10" < "E2" en string sort).
function numFromCodigo(codigo) {
  const m = (codigo || '').match(/(\d+)$/)
  return m ? parseInt(m[1], 10) : 0
}

const estandaresOrdenados = computed(() =>
  [...(estandares.data || [])].sort((a, b) => numFromCodigo(a.em_codigo) - numFromCodigo(b.em_codigo)),
)

function criteriosDe(emCodigo) {
  return (criterios.data || [])
    .filter((c) => c.cr_padre === emCodigo)
    .sort((a, b) => (a.cr_codigo || '').localeCompare(b.cr_codigo, 'es', { numeric: true }))
}

const informeUrl = computed(() =>
  `/api/method/frappe.utils.print_format.download_pdf?doctype=Autoevaluacion&name=${encodeURIComponent(props.name)}&format=${encodeURIComponent(PRINT_FORMAT)}`,
)
</script>

<template>
  <ScrollArea class="min-h-0 flex-1">
    <div class="mx-auto max-w-6xl px-6 py-8 sm:px-8 xl:px-10">
      <LoadingText v-if="doc.loading && !doc.doc" />
      <ErrorMessage v-else-if="doc.error" :message="doc.error.message" />

      <template v-else-if="doc.doc">
        <div class="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <div class="text-xs font-semibold uppercase tracking-wide text-ink-gray-5">Autoevaluación</div>
            <h1 class="font-display text-2xl font-bold text-ink-gray-9">{{ doc.doc.codigo }}</h1>
            <p class="mt-1 text-p-sm text-ink-gray-6">
              {{ doc.doc.marco_normativo }} · {{ doc.doc.estado }}
              <span v-if="doc.doc.avance_pct != null"> · {{ doc.doc.avance_pct }}% de avance</span>
            </p>
          </div>
          <a :href="informeUrl" target="_blank">
            <Button variant="solid">
              <template #prefix><span class="lucide-file-text size-4" aria-hidden="true" /></template>
              Generar informe (PDF)
            </Button>
          </a>
        </div>

        <LoadingText v-if="estandares.loading && !estandares.data" />
        <ErrorMessage v-else-if="estandares.error" :message="estandares.error.message" />

        <div v-else class="space-y-5">
          <EstandarCard v-for="e in estandaresOrdenados" :key="e.name" :row="e">
            <template #criterios>
              <div v-if="criterios.loading && !criterios.data" class="text-p-xs text-ink-gray-4">Cargando criterios…</div>
              <CriterioRow v-for="c in criteriosDe(e.em_codigo)" :key="c.name" :row="c" />
            </template>
          </EstandarCard>
        </div>
      </template>
    </div>
  </ScrollArea>
</template>
