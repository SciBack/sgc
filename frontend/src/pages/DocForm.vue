<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, ErrorMessage, LoadingText, ScrollArea, useDoc, useDoctype } from 'frappe-ui'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
import FieldInput from '@/components/form/FieldInput.vue'

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, required: true },
})

const router = useRouter()
const isNew = computed(() => props.name === 'new')

const { meta, loading: metaLoading, error: metaError } = useDoctypeMeta(props.doctype)

const doc = useDoc({
  doctype: props.doctype,
  name: computed(() => (isNew.value ? '' : props.name)),
})

const docType = useDoctype(props.doctype)

// Copia local editable — el doc de useDoc es de solo lectura (viene del
// store compartido); acá vive el borrador que edita el usuario.
const values = reactive({})
const saved = ref(false)
const saveError = ref(null)
const saving = ref(false)

// Campos visibles del formulario: sin ocultos ni de solo-lectura del sistema
// (name/owner/creation/... no vienen en meta.fields — ver useDoctypeMeta).
const visibleFields = computed(() =>
  (meta.value?.fields || []).filter((f) => !f.hidden),
)

function seedValuesFromDoc(source) {
  for (const f of visibleFields.value) {
    values[f.fieldname] = source?.[f.fieldname] ?? (f.fieldtype === 'Check' ? 0 : null)
  }
}

watch([() => doc.doc, meta], ([d, m]) => {
  if (!m) return
  if (isNew.value) {
    seedValuesFromDoc({})
  } else if (d) {
    seedValuesFromDoc(d)
  }
}, { immediate: true })

const title = computed(() => {
  if (isNew.value) return `Nuevo · ${props.doctype}`
  const tf = meta.value?.titleField
  return (tf && values[tf]) || props.name
})

function deskUrl() {
  const slug = props.doctype.toLowerCase().replace(/ /g, '-')
  return isNew.value ? `/app/${slug}/new` : `/app/${slug}/${encodeURIComponent(props.name)}`
}

async function save() {
  saveError.value = null
  saved.value = false
  saving.value = true
  try {
    const editable = {}
    for (const f of visibleFields.value) {
      if (f.fieldtype === 'Table' || f.read_only) continue
      editable[f.fieldname] = values[f.fieldname]
    }
    if (isNew.value) {
      const created = await docType.insert.submit(editable)
      saving.value = false
      router.replace({ name: 'DocForm', params: { doctype: props.doctype, name: created.name } })
      return
    }
    await doc.setValue.submit(editable)
    saved.value = true
    setTimeout(() => (saved.value = false), 2500)
  } catch (e) {
    saveError.value = e
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <ScrollArea class="min-h-0 flex-1">
    <div class="mx-auto max-w-3xl px-5 py-6 sm:px-8">
      <div class="mb-5 flex items-start justify-between gap-4">
        <div>
          <div class="text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ doctype }}</div>
          <h1 class="font-display text-2xl font-bold text-ink-gray-9">{{ title }}</h1>
        </div>
        <a :href="deskUrl()" target="_blank" class="whitespace-nowrap text-p-sm text-ink-gray-5 hover:text-ink-gray-8 hover:underline">
          Ver en el Desk
        </a>
      </div>

      <LoadingText v-if="metaLoading || (!isNew && doc.loading && !doc.doc)" />
      <ErrorMessage v-else-if="metaError" :message="metaError.message" />
      <ErrorMessage v-else-if="!isNew && doc.error" :message="doc.error.message" />

      <form v-else class="space-y-4" @submit.prevent="save">
        <div v-for="f in visibleFields" :key="f.fieldname">
          <FieldInput v-model="values[f.fieldname]" :field="f" :read-only="Boolean(f.read_only)" />
        </div>

        <div class="flex items-center gap-3 border-t border-outline-gray-1 pt-4">
          <Button variant="solid" type="submit" :loading="saving">
            {{ isNew ? 'Crear' : 'Guardar' }}
          </Button>
          <span v-if="saved" class="text-p-sm text-ink-green-6">Guardado.</span>
          <ErrorMessage v-if="saveError" :message="saveError.message" />
        </div>
      </form>
    </div>
  </ScrollArea>
</template>
