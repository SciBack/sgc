<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, ErrorMessage, LoadingText, ScrollArea, call, useDoc, useDoctype } from 'frappe-ui'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
import FieldInput from '@/components/form/FieldInput.vue'
import DocConnections from '@/components/form/DocConnections.vue'

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

// Última versión conocida del doc en el servidor. Sirve de base para el guardado
// completo (frappe.client.save) — se refresca tras cada guardado para no reenviar
// un `modified` viejo (evita el conflicto "Document has been modified") ni filas
// hijas sin `name` (que Frappe interpretaría como filas nuevas duplicadas).
const currentDoc = ref(null)

// Todos los campos del doctype (sin los ocultos): base para poblar y guardar.
const formFields = computed(() =>
  (meta.value?.fields || []).filter((f) => !f.hidden),
)

function hasContent(v) {
  return v !== null && v !== undefined && v !== '' && v !== 0
}

// Evalúa el `depends_on` de un campo (mismo mecanismo que el Desk) para no
// mostrar campos que no aplican — p.ej. `archivo` cuando el tipo es Enlace. La
// expresión viene del meta del propio sistema (confiable); ante cualquier error
// se muestra el campo (fail-open, nunca ocultar por un fallo de evaluación).
function passesDependsOn(expr, doc) {
  if (!expr) return true
  const code = expr.startsWith('eval:') ? expr.slice(5) : `doc.${expr}`
  try {
    return !!new Function('doc', `return (${code})`)(doc)
  } catch {
    return true
  }
}

// Campos que se RENDERIZAN: se ocultan (a) los de solo-lectura vacíos —
// metadatos del sistema (MIME, hash, cargado_por, URI, origen…) que solo hacen
// ruido cuando no tienen valor; los de solo-lectura CON valor (código, fechas,
// semáforo) sí se ven — y (b) los que su `depends_on` excluye.
const visibleFields = computed(() =>
  formFields.value.filter((f) => {
    if (f.read_only && !hasContent(values[f.fieldname])) return false
    if (!passesDependsOn(f.depends_on, values)) return false
    return true
  }),
)

function seedValuesFromDoc(source) {
  for (const f of formFields.value) {
    values[f.fieldname] = source?.[f.fieldname] ?? (f.fieldtype === 'Check' ? 0 : null)
  }
}

watch([() => doc.doc, meta], ([d, m]) => {
  if (!m) return
  if (isNew.value) {
    seedValuesFromDoc({})
  } else if (d) {
    currentDoc.value = d
    seedValuesFromDoc(d)
  }
}, { immediate: true })

// ¿El doctype tiene tablas hijas? Determina el camino de guardado en UPDATE.
const hasTableFields = computed(() =>
  formFields.value.some((f) => f.fieldtype === 'Table'),
)

const title = computed(() => {
  if (isNew.value) return `Nuevo · ${props.doctype}`
  const tf = meta.value?.titleField
  return (tf && values[tf]) || props.name
})

function deskUrl() {
  const slug = props.doctype.toLowerCase().replace(/ /g, '-')
  return isNew.value ? `/app/${slug}/new` : `/app/${slug}/${encodeURIComponent(props.name)}`
}

// Extrae un mensaje legible del error de frappe-ui/Frappe (que a veces trae
// HTML o viene envuelto). Evita el "Cannot read properties of null" cuando el
// guardado falla y `submit` no rejecta sino que deja el error en el recurso.
function errorMessage(err, fallback) {
  const raw =
    err?.messages?.[0] ||
    err?.message ||
    (typeof err === 'string' ? err : '') ||
    fallback
  return String(raw).replace(/<[^>]+>/g, '').trim() || fallback
}

// Valor de una fila hija normalizado a array (el modelo puede venir null).
function tableRows(fieldname) {
  const v = values[fieldname]
  return Array.isArray(v) ? v : []
}

async function save() {
  saveError.value = null
  saved.value = false
  saving.value = true
  try {
    if (isNew.value) {
      // INSERT: incluimos las tablas hijas en el payload — Frappe acepta el array
      // de filas al crear el documento.
      const editable = {}
      for (const f of formFields.value) {
        if (f.read_only) continue
        editable[f.fieldname] = f.fieldtype === 'Table' ? tableRows(f.fieldname) : values[f.fieldname]
      }
      const created = await docType.insert.submit(editable)
      // insert.submit puede resolver a null y dejar el error en docType.insert.error
      // (p.ej. 403 de permisos): mostrar el motivo real, no reventar en created.name.
      if (!created?.name) {
        throw new Error(errorMessage(docType.insert.error, 'No se pudo crear el registro.'))
      }
      saving.value = false
      router.replace({ name: 'DocForm', params: { doctype: props.doctype, name: created.name } })
      return
    }

    if (hasTableFields.value) {
      // UPDATE con tablas hijas: frappe.client.set_value NO persiste child tables,
      // así que guardamos el DOCUMENTO COMPLETO. Partimos de la última versión
      // conocida del servidor y superponemos los campos editables (escalares y
      // arrays de filas), preservando los read_only tal cual venían.
      const fullDoc = {
        ...(currentDoc.value || {}),
        doctype: props.doctype,
        name: props.name,
      }
      for (const f of formFields.value) {
        if (f.read_only) continue
        fullDoc[f.fieldname] = f.fieldtype === 'Table' ? tableRows(f.fieldname) : values[f.fieldname]
      }
      // call() rechaza ante error → lo captura el catch; si resolviera a algo sin
      // name, lo tratamos como fallo (mismo criterio que el resto del guardado).
      const savedDoc = await call('frappe.client.save', { doc: fullDoc })
      if (!savedDoc?.name) {
        throw new Error(errorMessage(savedDoc, 'No se pudieron guardar los cambios.'))
      }
      // Refrescamos base y borrador con el doc normalizado por el servidor (filas
      // hijas ya con `name`, `modified` al día) para que un segundo guardado no
      // choque ni duplique filas.
      currentDoc.value = savedDoc
      seedValuesFromDoc(savedDoc)
    } else {
      // Camino histórico para docs SIN tablas (Evidencia, Documento Controlado):
      // set_value puntual, sin tocar nada más, para no arriesgar regresiones.
      const editable = {}
      for (const f of formFields.value) {
        if (f.read_only) continue
        editable[f.fieldname] = values[f.fieldname]
      }
      await doc.setValue.submit(editable)
      if (doc.setValue.error) {
        throw new Error(errorMessage(doc.setValue.error, 'No se pudieron guardar los cambios.'))
      }
    }
    saved.value = true
    setTimeout(() => (saved.value = false), 2500)
  } catch (e) {
    saveError.value = { message: errorMessage(e, 'No se pudo guardar.') }
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
          <FieldInput
            v-model="values[f.fieldname]"
            :field="f"
            :read-only="Boolean(f.read_only)"
            :doctype="doctype"
            :docname="name"
          />
        </div>

        <div class="flex items-center gap-3 border-t border-outline-gray-1 pt-4">
          <Button variant="solid" type="submit" :loading="saving">
            {{ isNew ? 'Crear' : 'Guardar' }}
          </Button>
          <span v-if="saved" class="text-p-sm text-ink-green-6">Guardado.</span>
          <ErrorMessage v-if="saveError" :message="saveError.message" />
        </div>
      </form>

      <!-- Conexiones (Document Links del meta): p.ej. Evidencia -> Trazabilidad -->
      <div v-if="!metaLoading && (meta?.links || []).length" class="mt-8 space-y-6 border-t border-outline-gray-1 pt-6">
        <DocConnections
          v-for="lnk in meta.links"
          :key="lnk.link_doctype + lnk.link_fieldname"
          :parent-doctype="doctype"
          :parent-name="name"
          :link="lnk"
        />
      </div>
    </div>
  </ScrollArea>
</template>
