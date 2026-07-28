<script setup>
import { useCall } from 'frappe-ui'
import { useRouter } from 'vue-router'
import Boton from '@/components/ui/Boton.vue'
import TituloPagina from '@/components/ui/TituloPagina.vue'
import AreaScroll from '@/components/ui/AreaScroll.vue'
import Cargando from '@/components/ui/Cargando.vue'
import Alerta from '@/components/ui/Alerta.vue'
import { DocText, List, Plus } from 'reicon-vue'

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
  <AreaScroll class="min-h-0 flex-1">
    <div class="mx-auto max-w-7xl px-6 py-8 sm:px-8 xl:px-10">
      <div class="sb-page-heading mb-6">
        <div class="flex min-w-0 items-start gap-3">
          <span class="sb-page-heading__icon" aria-hidden="true"><List :size="20" /></span>
          <div>
            <div class="sb-section-label">Gestión de registros</div>
            <TituloPagina :title="doctype" class="mt-1" />
            <p class="mt-1 text-sm text-tinta-tenue">Registros disponibles, ordenados por su última actualización.</p>
          </div>
        </div>
        <Boton variante="primario" class="shrink-0" :route="{ name: 'DocNew', params: { doctype } }">
          <Plus :size="16" aria-hidden="true" />
          Nuevo
        </Boton>
      </div>

      <Cargando v-if="list.loading && !list.data" />
      <Alerta v-else-if="list.error" :message="list.error.message" />
      <p v-else-if="!list.data?.length" class="sb-empty-state text-sm">
        Sin registros todavía.
      </p>
      <div v-else class="sb-card w-full overflow-hidden">
        <div class="grid grid-cols-[minmax(0,1fr)_auto] gap-4 border-b border-borde bg-superficie-2 px-5 py-3 sm:grid-cols-[minmax(0,1fr)_11rem_4rem]">
          <span class="sb-section-label">Registro</span>
          <span class="sb-section-label hidden sm:block">Actualizado</span>
          <span class="hidden sm:block" aria-hidden="true" />
        </div>
        <div class="divide-y divide-borde">
          <div
            v-for="item in list.data"
            :key="item.name"
            class="group grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-5 py-3.5 transition-colors duration-150 hover:bg-superficie-2 sm:grid-cols-[minmax(0,1fr)_11rem_4rem]"
          >
            <button
              type="button"
              class="btn-press flex min-w-0 items-center gap-3 text-left"
              @click="openRow(item.name)"
            >
              <span class="flex size-9 shrink-0 items-center justify-center rounded-xl bg-marca-primaria-50 text-marca-primaria-700">
                <DocText :size="16" aria-hidden="true" />
              </span>
              <span class="min-w-0">
                <span class="block truncate text-sm font-semibold text-tinta">{{ item.name }}</span>
                <span class="mt-0.5 block text-xs text-tinta-tenue sm:hidden">{{ formatModified(item.modified) }}</span>
              </span>
            </button>
            <time class="hidden text-right text-xs text-tinta-tenue sm:block">{{ formatModified(item.modified) }}</time>
            <a
              :href="deskUrl(item.name)"
              target="_blank"
              class="justify-self-end rounded-lg px-2 py-1 text-xs font-semibold text-tinta-tenue transition-colors hover:bg-marca-primaria-50 hover:text-marca-primaria-700"
              @click.stop
            >
              Desk
            </a>
          </div>
        </div>
      </div>
      <p class="mt-4 text-xs text-tinta-tenue">
        Vista genérica dirigida por metadata (F2). El enlace "Desk" es un acceso directo de respaldo
        para administración.
      </p>
    </div>
  </AreaScroll>
</template>
