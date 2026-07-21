<script setup>
import { computed } from 'vue'
import { useCall, ErrorMessage, LoadingText, PageHeaderTitle, ScrollArea } from 'frappe-ui'

const CATEGORIA_LABEL = {
  Acreditacion: 'Acreditación',
  Gestion: 'Gestión',
  Proceso: 'Proceso',
  Satisfaccion: 'Satisfacción',
  Otra: 'Otros',
}

// "Valor Indicador" ya trae los cálculos del motor (scripts/indicadores);
// acá solo se leen y se agrupan por categoría del Indicador padre — sin
// reconstruir el motor en el cliente (ver plan §11).
const values = useCall({
  url: '/api/v2/method/frappe.client.get_list',
  params: {
    doctype: 'Valor Indicador',
    fields: JSON.stringify([
      'name', 'indicador', 'valor_num', 'valor_texto', 'fuente', 'fecha',
      'indicador.nombre as indicador_nombre',
      'indicador.codigo as indicador_codigo',
      'indicador.categoria as categoria',
    ]),
    order_by: 'fecha desc',
    limit_page_length: 200,
  },
  refetch: true,
  cacheKey: ['tablero', 'valor-indicador'],
})

const grouped = computed(() => {
  const rows = values.data || []
  // Un indicador puede tener varios cálculos históricos; nos quedamos con el
  // más reciente por indicador (ya vienen ordenados fecha desc).
  const latestByIndicador = new Map()
  for (const r of rows) {
    if (!latestByIndicador.has(r.indicador)) latestByIndicador.set(r.indicador, r)
  }
  const byCategoria = {}
  for (const r of latestByIndicador.values()) {
    const cat = r.categoria || 'Otra'
    byCategoria[cat] ||= []
    byCategoria[cat].push(r)
  }
  return Object.entries(byCategoria)
    .map(([cat, items]) => ({
      categoria: cat,
      label: CATEGORIA_LABEL[cat] || cat,
      items: items.sort((a, b) => (a.indicador_codigo || '').localeCompare(b.indicador_codigo || '')),
    }))
    .sort((a, b) => a.label.localeCompare(b.label))
})

function displayValue(row) {
  if (row.valor_num != null) return row.valor_num.toLocaleString('es-PE', { maximumFractionDigits: 2 })
  return row.valor_texto || '—'
}
</script>

<template>
  <ScrollArea class="min-h-0 flex-1">
    <div class="mx-auto max-w-6xl px-6 py-8 sm:px-8 xl:px-10">
      <section class="sb-hero mb-8 px-6 py-7 text-white sm:px-8">
        <div class="relative z-10 flex items-start gap-4">
          <span class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-white/10 text-marca-secundaria-300">
            <span class="lucide-chart-no-axes-column-increasing size-5" aria-hidden="true" />
          </span>
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.14em] text-white/65">Seguimiento institucional</p>
            <PageHeaderTitle title="Tablero de indicadores" class="mt-1 text-white [&_h1]:text-white" />
            <p class="mt-2 max-w-2xl text-p-sm leading-6 text-white/75">
              Último valor calculado por indicador, agrupado por categoría.
            </p>
          </div>
        </div>
      </section>

      <LoadingText v-if="values.loading && !values.data" />
      <ErrorMessage v-else-if="values.error" :message="values.error.message" />
      <p v-else-if="!grouped.length" class="sb-empty-state text-p-sm">
        Todavía no hay valores calculados en este entorno. El motor de indicadores corre contra Oracle
        LAMB — en producción ya hay valores reales; en el lab de desarrollo esta tabla está vacía.
      </p>

      <section v-for="group in grouped" :key="group.categoria" class="mb-7">
        <h2 class="sb-section-label mb-3 flex items-center gap-2">
          <span class="h-1.5 w-1.5 rounded-full bg-marca-secundaria-500" aria-hidden="true" />
          {{ group.label }}
        </h2>
        <div class="sb-card divide-y divide-outline-gray-1 overflow-hidden">
          <div
            v-for="row in group.items"
            :key="row.indicador"
            class="flex items-center justify-between gap-4 px-5 py-4"
          >
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="rounded-lg bg-marca-primaria-50 px-2 py-1 font-mono text-xs font-semibold text-marca-primaria-700">
                  {{ row.indicador_codigo }}
                </span>
                <span class="truncate text-p-sm text-ink-gray-8">{{ row.indicador_nombre }}</span>
              </div>
              <div class="mt-0.5 text-p-xs text-ink-gray-4">{{ row.fuente }} · {{ row.fecha }}</div>
            </div>
            <div class="font-display text-2xl font-bold tabular-nums text-marca-primaria-700">{{ displayValue(row) }}</div>
          </div>
        </div>
      </section>
    </div>
  </ScrollArea>
</template>
