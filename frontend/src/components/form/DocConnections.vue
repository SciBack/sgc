<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useCall, useDoctype } from 'frappe-ui'
import { Plus, X } from 'reicon-vue'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
import Boton from '@/components/ui/Boton.vue'
import Alerta from '@/components/ui/Alerta.vue'
import FieldInput from './FieldInput.vue'

// Conexiones de un documento: lista y crea los registros de otro DocType que
// apuntan a este (bloque `links` del meta). Para Evidencia son sus Trazabilidad
// (evidencia -> elemento del marco / proceso). Equivale a la sección Connections
// del Desk, pero usable desde la SPA.
const props = defineProps({
  parentDoctype: { type: String, required: true },
  parentName: { type: String, required: true },
  // { link_doctype, link_fieldname, group }
  link: { type: Object, required: true },
})

const linkDoctype = computed(() => props.link.link_doctype)
const fk = computed(() => props.link.link_fieldname)
const title = computed(() => props.link.group || linkDoctype.value)
const isNew = computed(() => !props.parentName || props.parentName === 'new')

const { meta } = useDoctypeMeta(linkDoctype.value)

// Campos editables del vínculo: sin el FK al padre (se autollena), ni de sistema.
const formFields = computed(() =>
  (meta.value?.fields || []).filter(
    (f) => f.fieldname !== fk.value && !f.hidden && !f.read_only,
  ),
)
// Campos con "sustancia" para el resumen de cada fila (Link/Select/Data).
const summaryFields = computed(() =>
  formFields.value.filter((f) => ['Link', 'Dynamic Link', 'Select', 'Data'].includes(f.fieldtype)),
)

const rows = ref([])
const listing = useCall({ url: '/api/v2/method/frappe.client.get_list', immediate: false })
const doc = useDoctype(linkDoctype.value)

async function reload() {
  if (isNew.value) {
    rows.value = []
    return
  }
  const res = await listing.submit({
    doctype: linkDoctype.value,
    filters: JSON.stringify({ [fk.value]: props.parentName }),
    fields: JSON.stringify(['name', ...formFields.value.map((f) => f.fieldname)]),
    limit_page_length: 0,
    order_by: 'creation desc',
  })
  rows.value = res || listing.data || []
}

// Recargar cuando ya hay meta (necesitamos los fields) y un padre real.
watch([meta, () => props.parentName], () => {
  if (meta.value && !isNew.value) reload()
}, { immediate: true })

function summaryOf(row) {
  return summaryFields.value
    .map((f) => row[f.fieldname])
    .filter((v) => v !== null && v !== undefined && v !== '')
}

// --- crear ---
const adding = ref(false)
const values = reactive({})
const saveError = ref(null)
const saving = ref(false)

function startAdd() {
  for (const f of formFields.value) values[f.fieldname] = f.fieldtype === 'Check' ? 0 : null
  saveError.value = null
  adding.value = true
}

async function saveLink() {
  saving.value = true
  saveError.value = null
  try {
    await doc.insert.submit({ [fk.value]: props.parentName, ...values })
    adding.value = false
    await reload()
  } catch (e) {
    saveError.value = e
  } finally {
    saving.value = false
  }
}

async function removeLink(name) {
  await doc.delete.submit(name)
  await reload()
}
</script>

<template>
  <section class="space-y-3">
    <div class="flex items-center justify-between">
      <h3 class="sb-field-label">{{ title }}</h3>
      <Boton v-if="!isNew && !adding" variante="fantasma" tamano="sm" @click="startAdd">
        <Plus :size="14" aria-hidden="true" />
        Vincular
      </Boton>
    </div>

    <p v-if="isNew" class="rounded-xl bg-superficie-2 px-3 py-2 text-p-xs text-tinta-tenue">
      Guarda primero para poder crear vínculos.
    </p>

    <template v-else>
      <ul v-if="rows.length" class="space-y-1.5">
        <li
          v-for="row in rows"
          :key="row.name"
          class="conn-row group flex items-center gap-2 rounded-xl border border-borde bg-superficie px-3 py-2"
        >
          <div class="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
            <span
              v-for="(v, i) in summaryOf(row)"
              :key="i"
              class="truncate rounded bg-superficie-3 px-1.5 py-0.5 text-p-xs text-tinta-suave"
            >{{ v }}</span>
          </div>
          <button
            type="button"
            class="conn-rm flex size-6 shrink-0 items-center justify-center rounded text-tinta-tenue opacity-0 hover:bg-superficie-3 hover:text-tinta-suave group-hover:opacity-100"
            title="Quitar vínculo"
            @click="removeLink(row.name)"
          >
            <X :size="14" aria-hidden="true" />
          </button>
        </li>
      </ul>
      <p v-else-if="!adding" class="text-p-xs text-tinta-tenue">Sin vínculos todavía.</p>

      <!-- alta inline -->
      <div v-if="adding" class="conn-form space-y-3 rounded-xl border border-borde-fuerte bg-superficie-2 p-4">
        <FieldInput
          v-for="f in formFields"
          :key="f.fieldname"
          v-model="values[f.fieldname]"
          :field="f"
        />
        <div class="flex items-center gap-2">
          <Boton variante="primario" tamano="sm" :cargando="saving" @click="saveLink">Guardar vínculo</Boton>
          <Boton variante="fantasma" tamano="sm" @click="adding = false">Cancelar</Boton>
          <Alerta v-if="saveError" :message="saveError.message" />
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.conn-row,
.conn-rm {
  transition: background-color 150ms ease, color 150ms ease, opacity 150ms ease,
    transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.conn-rm:active { transform: scale(0.92); }

.conn-form {
  transition: opacity 200ms cubic-bezier(0.23, 1, 0.32, 1),
    transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
@starting-style {
  .conn-form { opacity: 0; transform: translateY(4px); }
}
@media (prefers-reduced-motion: reduce) {
  .conn-row, .conn-rm, .conn-form { transition-property: background-color, color, opacity; }
}
</style>
