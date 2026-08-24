<script setup>
/**
 * Tabla de datos sobre TanStack Table, que es lo que manda el stack canónico.
 *
 * Dos decisiones que conviene no revertir sin leer esto:
 *
 * 1. **El estado vive en el servidor.** Orden y filtros NO se resuelven en el
 *    cliente: se emiten hacia arriba para que la consulta los mande a Frappe,
 *    que ya sabe hacerlo y respeta permisos por fila. Ordenar en cliente sobre
 *    una página de 50 registros da un orden falso —ordena lo que se trajo, no
 *    lo que hay—, y ese es justo el tipo de mentira silenciosa que un sistema
 *    de calidad no se puede permitir. Por eso `manualSorting: true`.
 *
 * 2. **Las columnas no se configuran aquí.** Llegan de fuera, derivadas del
 *    meta del DocType (`in_list_view`). Configurarlas a mano por pantalla es
 *    lo que tenía la lista antes —dos columnas fijas para los 39 DocTypes— y
 *    obliga a tocar código cada vez que Calidad decide qué quiere ver.
 */
import { computed } from 'vue'
import {
  FlexRender, getCoreRowModel, useVueTable,
} from '@tanstack/vue-table'
import { AngleDown } from 'reicon-vue'

const props = defineProps({
  // [{ key, label, formato? }] — derivadas del meta por el llamador.
  columnas: { type: Array, required: true },
  filas: { type: Array, default: () => [] },
  // { campo, desc } — el orden vigente, resuelto en servidor.
  orden: { type: Object, default: () => ({ campo: 'modified', desc: true }) },
  // Filtros declarados por el DocType, indexados por campo. Se pintan DEBAJO de
  // la cabecera de su columna, no en una caja aparte: así se ve de un vistazo
  // qué columna está filtrada y por qué valor, en vez de tener que cruzar dos
  // sitios de la pantalla.
  filtros: { type: Object, default: () => ({}) },
  valores: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['ordenar', 'abrir', 'filtrar'])

const hayFiltros = computed(() =>
  props.columnas.some((c) => props.filtros[c.key]),
)

const columnDefs = computed(() =>
  props.columnas.map((c) => ({
    accessorKey: c.key,
    header: c.label,
    cell: (info) => {
      const v = info.getValue()
      return c.formato ? c.formato(v, info.row.original) : (v ?? '—')
    },
  })),
)

const table = useVueTable({
  get data() {
    return props.filas
  },
  get columns() {
    return columnDefs.value
  },
  getCoreRowModel: getCoreRowModel(),
  manualSorting: true,
})

function alternarOrden(campo) {
  const mismo = props.orden.campo === campo
  emit('ordenar', { campo, desc: mismo ? !props.orden.desc : false })
}
</script>

<template>
  <div class="overflow-x-auto rounded-xl border border-borde">
    <table class="w-full min-w-[36rem] border-collapse text-sm">
      <thead>
        <tr class="border-b border-borde bg-superficie-tenue">
          <th
            v-for="col in columnas"
            :key="col.key"
            scope="col"
            class="px-4 py-2.5 text-left"
          >
            <button
              type="button"
              class="inline-flex items-center gap-1 text-[0.68rem] font-bold uppercase tracking-[0.06em] text-tinta-suave transition-colors hover:text-tinta"
              :aria-sort="orden.campo === col.key ? (orden.desc ? 'descending' : 'ascending') : 'none'"
              @click="alternarOrden(col.key)"
            >
              {{ col.label }}
              <AngleDown
                v-if="orden.campo === col.key"
                :size="12"
                class="transition-transform"
                :class="!orden.desc && 'rotate-180'"
                aria-hidden="true"
              />
            </button>
          </th>
        </tr>
        <!-- Fila de filtros, alineada con su columna. Solo aparece si alguna
             columna declara filtro; una fila vacía sería ruido. -->
        <tr v-if="hayFiltros" class="border-b border-borde bg-superficie-tenue">
          <th v-for="col in columnas" :key="`f-${col.key}`" class="px-3 py-2 text-left font-normal">
            <select
              v-if="filtros[col.key]?.opciones"
              class="border-input h-8 w-full rounded-lg border bg-transparent px-2 text-xs"
              :value="valores[col.key] ?? ''"
              :aria-label="`Filtrar por ${col.label}`"
              @change="emit('filtrar', { campo: col.key, valor: $event.target.value || null })"
            >
              <option value="">Todos</option>
              <option v-for="o in filtros[col.key].opciones" :key="o" :value="o">{{ o }}</option>
            </select>
            <input
              v-else-if="filtros[col.key]"
              type="text"
              class="border-input h-8 w-full rounded-lg border bg-transparent px-2 text-xs"
              :value="valores[col.key] ?? ''"
              :placeholder="`Filtrar…`"
              :aria-label="`Filtrar por ${col.label}`"
              @change="emit('filtrar', { campo: col.key, valor: $event.target.value || null })"
            />
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="fila in table.getRowModel().rows"
          :key="fila.id"
          class="cursor-pointer border-b border-borde/60 transition-colors last:border-0 hover:bg-superficie-tenue"
          @click="emit('abrir', fila.original.name)"
        >
          <td v-for="celda in fila.getVisibleCells()" :key="celda.id" class="px-4 py-3 text-tinta">
            <FlexRender :render="celda.column.columnDef.cell" :props="celda.getContext()" />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
