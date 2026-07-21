<script setup>
import { useCall } from 'frappe-ui'
import { useRouter } from 'vue-router'
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

function formatModified(value) {
  if (!value) return 'Sin fecha'
  const date = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('es-PE', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
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
      <div v-else class="sb-card w-full overflow-hidden">
        <div class="grid grid-cols-[minmax(0,1fr)_auto] gap-4 border-b border-outline-gray-1 bg-surface-gray-1 px-5 py-3 sm:grid-cols-[minmax(0,1fr)_11rem_4rem]">
          <span class="sb-section-label">Registro</span>
          <span class="sb-section-label hidden sm:block">Actualizado</span>
          <span class="hidden sm:block" aria-hidden="true" />
        </div>
        <div class="divide-y divide-outline-gray-1">
          <div
            v-for="item in list.data"
            :key="item.name"
            class="group grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-5 py-3.5 transition-colors duration-150 hover:bg-surface-gray-1 sm:grid-cols-[minmax(0,1fr)_11rem_4rem]"
          >
            <button
              type="button"
              class="btn-press flex min-w-0 items-center gap-3 text-left"
              @click="openRow(item.name)"
            >
              <span class="flex size-9 shrink-0 items-center justify-center rounded-xl bg-marca-primaria-50 text-marca-primaria-700">
                <span class="lucide-file-text size-4" aria-hidden="true" />
              </span>
              <span class="min-w-0">
                <span class="block truncate text-p-base font-semibold text-ink-gray-8">{{ item.name }}</span>
                <span class="mt-0.5 block text-p-xs text-ink-gray-5 sm:hidden">{{ formatModified(item.modified) }}</span>
              </span>
            </button>
            <time class="hidden text-right text-p-xs text-ink-gray-5 sm:block">{{ formatModified(item.modified) }}</time>
            <a
              :href="deskUrl(item.name)"
              target="_blank"
              class="justify-self-end rounded-lg px-2 py-1 text-p-xs font-semibold text-ink-gray-5 transition-colors hover:bg-marca-primaria-50 hover:text-marca-primaria-700"
              @click.stop
            >
              Desk
            </a>
          </div>
        </div>
      </div>
      <p class="mt-4 text-p-xs text-ink-gray-5">
        Vista genérica dirigida por metadata (F2). El enlace "Desk" es un acceso directo de respaldo
        para administración.
      </p>
    </div>
  </ScrollArea>
</template>
