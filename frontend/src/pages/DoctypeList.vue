<script setup>
import { computed, reactive } from 'vue'
import { useCall } from 'frappe-ui'
import { useRouter } from 'vue-router'
import Boton from '@/components/ui/Boton.vue'
import TituloPagina from '@/components/ui/TituloPagina.vue'
import AreaScroll from '@/components/ui/AreaScroll.vue'
import Cargando from '@/components/ui/Cargando.vue'
import Alerta from '@/components/ui/Alerta.vue'
import TablaDatos from '@/components/ui/TablaDatos.vue'
import { List, Plus } from 'reicon-vue'
import { puede } from '@/composables/usePermisos'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
import { camposAConsultar, columnasDeMeta, filtrosDeMeta } from '@/composables/useListaDeMeta'

const router = useRouter()

// Lista GENÉRICA dirigida por el meta del DocType. Antes pedía dos campos fijos
// —`name` y `modified`— para los 39 DocTypes, así que en «Proceso» se veía «S04»
// y una fecha cuando el sistema ya tenía escrito que se muestren código, nombre
// y nivel, y que se filtre por nivel y estado. Nada de eso se configura aquí:
// sale de `in_list_view` e `in_standard_filter`.
const props = defineProps({ doctype: { type: String, required: true } })

const puedeCrear = computed(() => puede(props.doctype, 'create'))

const { meta, loading: metaLoading } = useDoctypeMeta(() => props.doctype)
const columnas = computed(() => columnasDeMeta(meta.value))
const filtrosDisponibles = computed(() => filtrosDeMeta(meta.value))

// Orden y filtros se resuelven EN EL SERVIDOR (canon del design system).
// Ordenar en cliente sobre una página de 50 ordenaría lo que se trajo, no lo que
// hay: un orden falso, y en un sistema de calidad eso no es un detalle.
const orden = reactive({ campo: 'modified', desc: true })
const filtros = reactive({})

const filtrosActivos = computed(() =>
  Object.fromEntries(Object.entries(filtros).filter(([, v]) => v !== null && v !== '')),
)

const list = useCall({
  // v2 (no v1): useCall espera el envelope {"data": [...]} de la API v2.
  url: '/api/v2/method/frappe.client.get_list',
  params: () => ({
    doctype: props.doctype,
    fields: JSON.stringify(camposAConsultar(columnas.value)),
    filters: JSON.stringify(filtrosActivos.value),
    order_by: `${orden.campo} ${orden.desc ? 'desc' : 'asc'}`,
    limit_page_length: 50,
  }),
  refetch: true,
})

// Los filtros, indexados por campo: la tabla los pinta bajo su columna.
const filtrosPorCampo = computed(() =>
  Object.fromEntries(filtrosDisponibles.value.map((f) => [f.key, f])),
)

function aplicarFiltro({ campo, valor }) {
  if (valor === null || valor === '') delete filtros[campo]
  else filtros[campo] = valor
}

function ordenarPor({ campo, desc }) {
  orden.campo = campo
  orden.desc = desc
}

function limpiarFiltros() {
  for (const k of Object.keys(filtros)) delete filtros[k]
}

const hayFiltros = computed(() => Object.keys(filtrosActivos.value).length > 0)

// La Autoevaluación tiene pantalla propia (flujo de valoración NL/L/LP); el
// resto usa el formulario genérico dirigido por metadata.
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
  return new Intl.DateTimeFormat('es-PE', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

// Columnas con su formato: las fechas se leen, no se muestran en crudo.
const columnasConFormato = computed(() =>
  columnas.value.map((c) => ({
    ...c,
    formato: ['Date', 'Datetime'].includes(c.fieldtype)
      ? (v) => (v ? formatModified(v) : '—')
      : undefined,
  })),
)
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
            <p class="mt-1 text-sm text-tinta-tenue">
              Registros disponibles. Pulsa una cabecera para ordenar.
            </p>
          </div>
        </div>
        <!-- Sin permiso de creación no se ofrece el botón: antes lo veía
             cualquiera y el rechazo llegaba al final del formulario. -->
        <Boton
          v-if="puedeCrear"
          variante="primario"
          class="shrink-0"
          :route="{ name: 'DocNew', params: { doctype } }"
        >
          <Plus :size="16" aria-hidden="true" />
          Nuevo
        </Boton>
      </div>

      <Cargando v-if="(list.loading && !list.data) || metaLoading" />
      <Alerta v-else-if="list.error" :message="list.error.message" />
      <p v-else-if="!list.data?.length" class="sb-empty-state text-sm">
        {{ hayFiltros ? 'Ningún registro coincide con el filtro.' : 'Sin registros todavía.' }}
      </p>
      <TablaDatos
        v-else
        :columnas="columnasConFormato"
        :filas="list.data"
        :orden="orden"
        :filtros="filtrosPorCampo"
        :valores="filtros"
        @ordenar="ordenarPor"
        @filtrar="aplicarFiltro"
        @abrir="openRow"
      />

      <p v-if="hayFiltros" class="mt-3 text-xs text-tinta-tenue">
        Filtrando. <button type="button" class="font-semibold underline" @click="limpiarFiltros">Quitar filtros</button>
      </p>

      <p class="mt-4 text-xs text-tinta-tenue">
        Columnas y filtros los declara el propio DocType; el orden se resuelve en el servidor.
      </p>
    </div>
  </AreaScroll>
</template>
