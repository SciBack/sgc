<script setup>
import { useCall } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { List, ListRow, ListRows, ListCell, ListHeader, ListHeaderCell } from 'frappe-ui/list'
import { Button, PageHeaderTitle, ScrollArea, LoadingText, ErrorMessage } from 'frappe-ui'

const router = useRouter()

// Vista de lista GENÉRICA — funciona para cualquier DocType con solo su
// nombre. Columnas mínimas (name + modified); el detalle/edición real ya
// vive en DocForm.vue (F2, dirigido por metadata) — cada fila navega ahí.
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

// La Autoevaluación tiene pantalla propia (flujo de valoración NL/L/LP); el
// resto de los DocTypes usa el formulario genérico dirigido por metadata.
function openRow(name) {
  if (props.doctype === 'Autoevaluacion') {
    router.push({ name: 'AutoevaluacionDetalle', params: { name } })
  } else {
    router.push({ name: 'DocForm', params: { doctype: props.doctype, name } })
  }
}
</script>

<template>
  <ScrollArea class="min-h-0 flex-1">
    <div class="mx-auto max-w-7xl px-6 py-8 sm:px-8 xl:px-10">
      <div class="sb-page-heading mb-6">
        <div class="flex min-w-0 items-start gap-3">
          <span class="sb-page-heading__icon" aria-hidden="true"><span class="lucide-list size-5" /></span>
          <div>
            <div class="sb-section-label">Gestión de registros</div>
            <PageHeaderTitle :title="doctype" class="mt-1" />
            <p class="mt-1 text-p-sm text-ink-gray-5">Registros disponibles, ordenados por su última actualización.</p>
          </div>
        </div>
        <Button variant="solid" class="sb-primary-action btn-press shrink-0" :route="{ name: 'DocNew', params: { doctype } }">
          <template #prefix><span class="lucide-plus size-4" aria-hidden="true" /></template>
          Nuevo
        </Button>
      </div>

      <LoadingText v-if="list.loading && !list.data" />
      <ErrorMessage v-else-if="list.error" :message="list.error.message" />
      <p v-else-if="!list.data?.length" class="sb-empty-state text-p-sm">
        Sin registros todavía.
      </p>
      <List v-else class="sb-card w-full overflow-hidden">
        <ListHeader>
          <ListHeaderCell>Registro</ListHeaderCell>
          <ListHeaderCell align="end">Modificado</ListHeaderCell>
          <ListHeaderCell />
        </ListHeader>
        <ListRows :items="list.data" v-slot="{ item, value }">
          <ListRow :value="value" class="cursor-pointer transition-colors duration-150 hover:bg-surface-gray-1" @click="openRow(item.name)">
            <ListCell>
              <span class="truncate text-base text-ink-gray-8">{{ item.name }}</span>
            </ListCell>
            <ListCell class="justify-end">
              <span class="text-sm text-ink-gray-5">{{ item.modified }}</span>
            </ListCell>
            <ListCell class="justify-end">
              <a
                :href="deskUrl(item.name)"
                target="_blank"
                class="text-p-xs text-ink-gray-4 hover:text-ink-gray-7 hover:underline"
                @click.stop
              >
                Desk
              </a>
            </ListCell>
          </ListRow>
        </ListRows>
      </List>
      <p class="mt-4 text-p-xs text-ink-gray-5">
        Vista genérica dirigida por metadata (F2). El enlace "Desk" es un acceso directo de respaldo
        para administración.
      </p>
    </div>
  </ScrollArea>
</template>
