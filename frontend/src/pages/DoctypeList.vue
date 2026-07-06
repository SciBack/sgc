<script setup>
import { useCall } from 'frappe-ui'
import { List, ListRow, ListRows, ListCell, ListHeader, ListHeaderCell } from 'frappe-ui/list'
import { PageHeaderTitle, ScrollArea, LoadingText, ErrorMessage } from 'frappe-ui'

// Vista de lista GENÉRICA — funciona para cualquier DocType con solo su
// nombre. Es deliberadamente mínima (name + modified): la vista completa
// dirigida por metadata (columnas reales, filtros, formulario) es F2 del
// plan (doc/specs/sgc-frappe/05-plan-frontend-spa.md §6). Por ahora,
// "ver en el Desk" cubre el detalle completo mientras se construye F2.
const props = defineProps({ doctype: { type: String, required: true } })

const list = useCall({
  // v2 (no v1): useCall espera el envelope {"data": [...]} de la API v2.
  url: '/api/v2/method/frappe.client.get_list',
  params: () => ({
    doctype: props.doctype,
    fields: JSON.stringify(['name', 'modified']),
    order_by: 'modified desc',
    limit_page_length: 50,
  }),
  refetch: true,
  cacheKey: ['list', props.doctype],
})

function deskUrl(name) {
  return `/app/${encodeURIComponent(props.doctype.toLowerCase().replace(/ /g, '-'))}/${encodeURIComponent(name)}`
}
</script>

<template>
  <ScrollArea class="min-h-0 flex-1">
    <div class="mx-auto max-w-4xl px-5 py-6 sm:px-8">
      <PageHeaderTitle :title="doctype" class="mb-4" />

      <LoadingText v-if="list.loading && !list.data" />
      <ErrorMessage v-else-if="list.error" :message="list.error.message" />
      <p v-else-if="!list.data?.length" class="text-p-sm text-ink-gray-6">
        Sin registros todavía.
      </p>
      <List v-else class="w-full">
        <ListHeader>
          <ListHeaderCell>Registro</ListHeaderCell>
          <ListHeaderCell align="end">Modificado</ListHeaderCell>
        </ListHeader>
        <ListRows :items="list.data" v-slot="{ item, value }">
          <ListRow :value="value">
            <a :href="deskUrl(item.name)" target="_blank" class="contents">
              <ListCell>
                <span class="truncate text-base text-ink-gray-8">{{ item.name }}</span>
              </ListCell>
              <ListCell class="justify-end">
                <span class="text-sm text-ink-gray-5">{{ item.modified }}</span>
              </ListCell>
            </a>
          </ListRow>
        </ListRows>
      </List>
      <p class="mt-4 text-p-xs text-ink-gray-5">
        Vista mínima (F1). El formulario completo dentro de la SPA llega en F2 — por ahora, cada
        fila abre el registro en el Desk de Frappe.
      </p>
    </div>
  </ScrollArea>
</template>
