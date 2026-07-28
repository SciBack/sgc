<script setup>
import { computed } from 'vue'
import { Button, LoadingText } from 'frappe-ui'
import { Plus, Trash } from 'reicon-vue'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
import FieldInput from './FieldInput.vue'

// Editor de tabla hija (fieldtype Table) para la SPA. Reutiliza FieldInput por
// celda, con las columnas tomadas del meta del child doctype (field.options).
// Equivale a la grilla de child tables del Desk, pero usable desde el formulario
// web — p.ej. las 8 condiciones CBC ('condiciones' del Informe Cumplimiento).
const props = defineProps({
  field: { type: Object, required: true }, // el campo Table; field.options = child doctype
  readOnly: { type: Boolean, default: false },
  doctype: { type: String, default: '' }, // contexto del padre (informativo)
  docname: { type: String, default: '' },
})

// v-model del array de filas; puede llegar null cuando aún no hay filas.
const rows = defineModel({ default: null })

const label = computed(() => props.field.label || props.field.fieldname)

const { meta, loading, error } = useDoctypeMeta(() => props.field.options)

// Columnas de la grilla: los campos marcados `in_list_view`. Si ninguno lo
// estuviera (child doctype sin columnas configuradas), caemos a los primeros
// campos no ocultos para no dejar la grilla vacía.
const columns = computed(() => {
  const fields = (meta.value?.fields || []).filter((f) => !f.hidden)
  const inList = fields.filter((f) => f.in_list_view)
  return inList.length ? inList : fields.slice(0, 4)
})

// Siempre trabajamos contra un array real, aunque el modelo venga null.
const safeRows = computed(() => (Array.isArray(rows.value) ? rows.value : []))

// Ancho de columnas: cada celda flexible con un mínimo legible; la última
// columna (auto) es la de la acción "eliminar" cuando es editable.
const gridStyle = computed(() => {
  const cells = columns.value.map(() => 'minmax(150px, 1fr)')
  if (!props.readOnly) cells.push('auto')
  return { gridTemplateColumns: cells.join(' ') }
})

function colLabel(col) {
  const base = col.label || col.fieldname
  return col.reqd ? `${base} *` : base
}

function addRow() {
  const blank = {}
  for (const col of columns.value) {
    blank[col.fieldname] = col.fieldtype === 'Check' ? 0 : null
  }
  rows.value = [...safeRows.value, blank]
}

function removeRow(idx) {
  const next = [...safeRows.value]
  next.splice(idx, 1)
  rows.value = next
}
</script>

<template>
  <div class="space-y-1.5">
    <label class="sb-field-label block">{{ label }}</label>

    <LoadingText v-if="loading" text="Cargando columnas…" />
    <p v-else-if="error" class="rounded bg-superficie-2 px-2.5 py-1.5 text-p-sm text-tinta-suave">
      No se pudieron cargar las columnas de «{{ field.options }}». Editar en el Desk.
    </p>

    <template v-else>
      <!-- Grilla: cabecera + una fila por registro. Scroll horizontal si no cabe. -->
      <div v-if="safeRows.length" class="ctf-scroll overflow-x-auto rounded-xl border border-borde-fuerte">
        <div class="ctf-grid" :style="gridStyle" role="table">
          <!-- cabecera -->
          <div
            v-for="col in columns"
            :key="`h-${col.fieldname}`"
            class="ctf-head"
          >{{ colLabel(col) }}</div>
          <div v-if="!readOnly" class="ctf-head ctf-head-action" aria-hidden="true"></div>

          <!-- filas -->
          <template v-for="(row, idx) in safeRows" :key="idx">
            <div
              v-for="col in columns"
              :key="`c-${idx}-${col.fieldname}`"
              class="ctf-cell"
            >
              <FieldInput
                v-model="row[col.fieldname]"
                :field="col"
                :read-only="readOnly || Boolean(col.read_only)"
                :doctype="field.options"
                hide-label
              />
            </div>
            <div v-if="!readOnly" class="ctf-cell ctf-cell-action">
              <button
                type="button"
                class="ctf-rm flex size-7 items-center justify-center rounded text-tinta-tenue hover:bg-superficie-3 hover:text-tinta-suave"
                title="Eliminar fila"
                aria-label="Eliminar fila"
                @click="removeRow(idx)"
              >
                <Trash :size="16" aria-hidden="true" />
              </button>
            </div>
          </template>
        </div>
      </div>

      <!-- estado vacío -->
      <p v-else class="ctf-empty rounded-xl border border-dashed border-borde-fuerte bg-superficie-2 px-3 py-3 text-center text-p-sm text-tinta-tenue">
        Sin filas todavía.
      </p>

      <Button v-if="!readOnly" variant="ghost" size="sm" class="ctf-add" @click="addRow">
        <template #prefix><Plus :size="14" /></template>
        Agregar fila
      </Button>
    </template>
  </div>
</template>

<style scoped>
.ctf-grid {
  display: grid;
  min-width: max-content;
  align-items: start;
}

/* Cabecera compacta, pegajosa sobre el borde superior de la grilla. */
.ctf-head {
  position: sticky;
  top: 0;
  padding: 0.375rem 0.625rem;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--color-tinta-tenue);
  background-color: var(--color-superficie-2);
  border-bottom: 1px solid var(--color-borde-fuerte);
}
.ctf-head-action {
  padding: 0;
}

.ctf-cell {
  padding: 0.5rem 0.625rem;
  border-bottom: 1px solid var(--color-borde);
}
.ctf-cell-action {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Aparición suave de la grilla y del estado vacío. */
.ctf-grid,
.ctf-empty {
  transition: opacity 200ms cubic-bezier(0.23, 1, 0.32, 1),
    transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
@starting-style {
  .ctf-grid,
  .ctf-empty {
    opacity: 0;
    transform: translateY(4px);
  }
}

.ctf-rm,
.ctf-add {
  transition: background-color 150ms ease, color 150ms ease,
    transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.ctf-rm:active {
  transform: scale(0.92);
}

@media (prefers-reduced-motion: reduce) {
  .ctf-grid,
  .ctf-empty,
  .ctf-rm,
  .ctf-add {
    transition-property: opacity, background-color, color;
  }
}
</style>
