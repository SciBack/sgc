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
      <PageHeaderTitle title="Tablero de indicadores" class="mb-1" />
      <p class="mb-5 text-p-sm text-ink-gray-6">
        Último valor calculado por indicador, agrupado por categoría. Los cálculos vienen del motor de
        indicadores (Oracle LAMB); acá solo se muestran.
      </p>

      <LoadingText v-if="values.loading && !values.data" />
      <ErrorMessage v-else-if="values.error" :message="values.error.message" />
      <p v-else-if="!grouped.length" class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 p-4 text-p-sm text-ink-gray-6">
        Todavía no hay valores calculados en este entorno. El motor de indicadores corre contra Oracle
        LAMB — en producción ya hay valores reales; en el lab de desarrollo esta tabla está vacía.
      </p>

      <section v-for="group in grouped" :key="group.categoria" class="mb-7">
        <h2 class="mb-2.5 border-b border-outline-gray-1 pb-2 text-sm-medium uppercase tracking-wide text-ink-gray-5">
          {{ group.label }}
        </h2>
        <div class="divide-y divide-outline-gray-1 rounded-lg border border-outline-gray-1 bg-surface-base">
          <div
            v-for="row in group.items"
            :key="row.indicador"
            class="flex items-center justify-between gap-4 px-4 py-3"
          >
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="rounded bg-surface-gray-2 px-1.5 py-0.5 font-mono text-xs font-semibold text-ink-gray-6">
                  {{ row.indicador_codigo }}
                </span>
                <span class="truncate text-p-sm text-ink-gray-8">{{ row.indicador_nombre }}</span>
              </div>
              <div class="mt-0.5 text-p-xs text-ink-gray-4">{{ row.fuente }} · {{ row.fecha }}</div>
            </div>
            <div class="font-display text-xl font-bold text-upeu-navy">{{ displayValue(row) }}</div>
          </div>
        </div>
      </section>
    </div>
  </ScrollArea>
</template>
