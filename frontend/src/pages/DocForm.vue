<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { call, useDoc, useDoctype } from 'frappe-ui'
import { FileContent, Link2 } from 'reicon-vue'
import Boton from '@/components/ui/Boton.vue'
import Alerta from '@/components/ui/Alerta.vue'
import Cargando from '@/components/ui/Cargando.vue'
import AreaScroll from '@/components/ui/AreaScroll.vue'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
import { puede, tieneFlujo as doctypeTieneFlujo } from '@/composables/usePermisos'
import { avisar } from '@/composables/useAvisos'
import { mensajeDeError } from '@/lib/mensajesFrappe'
import FieldInput from '@/components/form/FieldInput.vue'
import DocConnections from '@/components/form/DocConnections.vue'
import WorkflowActions from '@/components/workflow/WorkflowActions.vue'

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, required: true },
})

const router = useRouter()
const isNew = computed(() => props.name === 'new')

// Qué puede hacer esta persona con este DocType (boot -> sgc/permisos_ui.py).
// `puedeGuardar` gobierna el botón; `sinPermiso` avisa ANTES de que rellene
// nada, en vez de dejar que llegue al final y reciba un rechazo del servidor.
const puedeGuardar = computed(() =>
  isNew.value ? puede(props.doctype, 'create') : puede(props.doctype, 'write'),
)
const sinPermiso = computed(() => !puedeGuardar.value)

const { meta, loading: metaLoading, error: metaError } = useDoctypeMeta(props.doctype)

const doc = useDoc({
  doctype: props.doctype,
  name: computed(() => (isNew.value ? '' : props.name)),
})

const docType = useDoctype(props.doctype)

// ¿Este documento se mueve por un ciclo de vida? La lista de DocTypes con
// workflow activo llega en el boot (ver `doctypes_con_flujo`).
//
// `WorkflowActions` existía desde hacía tiempo y estaba conectado ÚNICAMENTE en
// la pantalla de Autoevaluación, así que catorce de los quince flujos no se
// podían recorrer desde la aplicación: se creaba el documento y se quedaba en su
// estado inicial para siempre, porque el formulario solo sabía guardar. No salió
// validando por API —ahí se llama a `apply_workflow` directamente— sino la
// primera vez que alguien se sentó a usar el sistema (2026-08-24).
const tieneFlujo = computed(() => !isNew.value && doctypeTieneFlujo(props.doctype))

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
  formFields.value
    .filter((f) => {
      if (f.read_only && !hasContent(values[f.fieldname])) return false
      if (!passesDependsOn(f.depends_on, values)) return false
      return true
    })
    // Frappe declara también obligatoriedad y solo-lectura CONDICIONALES. Se
    // resuelven con el mismo evaluador que `depends_on` y se entregan ya
    // resueltas al campo, para que la interfaz no tenga que saber nada de
    // expresiones. Si no se leen, un campo obligatorio solo en cierto estado se
    // pinta siempre igual y la regla vive únicamente en el servidor: la persona
    // se entera al recibir el rechazo.
    .map((f) => ({
      ...f,
      reqd: f.reqd || (f.mandatory_depends_on
        ? passesDependsOn(f.mandatory_depends_on, values)
        : false),
      read_only: f.read_only || (f.read_only_depends_on
        ? passesDependsOn(f.read_only_depends_on, values)
        : false),
    })),
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
// El mensaje lo escribe Frappe (`_server_messages`), aquí solo se lee: ver
// `lib/mensajesFrappe`. Un texto propio dice menos —«No se pudo crear el
// registro» frente a «falta el valor para Documento Controlado: Tipo de
// documento»— y encima se desincroniza: cada validación nueva del servidor
// nacería muda en la interfaz.
function errorMessage(err, fallback) {
  return mensajeDeError(err, fallback)
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
      // El aviso va ANTES de navegar: el mensaje inline del formulario se
      // perdía en el salto a la ficha nueva, así que crear algo no confirmaba
      // nada. La pila de avisos vive en el shell y sobrevive al cambio de ruta.
      avisar(`${props.doctype} creado`, 'exito', { detalle: created.name })
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
    avisar('Cambios guardados', 'exito')
    setTimeout(() => (saved.value = false), 2500)
  } catch (e) {
    saveError.value = { message: errorMessage(e, 'No se pudo guardar.') }
    // También como aviso: el mensaje inline queda al pie del formulario y en un
    // documento largo se pulsa «Guardar» sin verlo.
    avisar('No se pudo guardar', 'error', { detalle: saveError.value.message })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AreaScroll class="min-h-0 flex-1">
    <div class="mx-auto max-w-3xl px-5 py-6 sm:px-8">
      <div class="sb-page-heading mb-6">
        <div class="flex min-w-0 items-start gap-3">
          <span class="sb-page-heading__icon" aria-hidden="true"><FileContent :size="20" /></span>
          <div>
            <div class="sb-section-label">{{ doctype }}</div>
            <h1 class="mt-1 font-display text-2xl font-bold text-tinta">{{ title }}</h1>
            <p class="mt-1 text-sm text-tinta-tenue">Completa los campos necesarios y guarda los cambios.</p>
          </div>
        </div>
        <a :href="deskUrl()" target="_blank" class="btn-press whitespace-nowrap rounded-xl border border-borde-fuerte px-3 py-2 text-sm font-semibold text-tinta-suave transition-colors hover:bg-superficie-2 hover:text-tinta">
          <Link2 :size="14" class="mr-1 inline align-text-bottom" aria-hidden="true" />
          Ver en el Desk
        </a>
      </div>

      <Cargando v-if="metaLoading || (!isNew && doc.loading && !doc.doc)" />
      <Alerta v-else-if="metaError" :message="metaError.message" />
      <Alerta v-else-if="!isNew && doc.error" :message="doc.error.message" />

      <!-- Aviso por delante: si no le corresponde, que lo sepa ANTES de
           rellenar el formulario entero, no al pulsar el botón. -->
      <Alerta
        v-else-if="sinPermiso"
        :message="
          isNew
            ? 'No tienes permiso para crear registros de este tipo. Puedes consultarlos, pero crearlos corresponde a otro rol.'
            : 'No tienes permiso para editar este documento. Puedes consultarlo; los cambios corresponden a otro rol.'
        "
      />

      <template v-else>
        <!-- Las acciones del flujo van ANTES del formulario: es lo que la
             persona viene a hacer cuando abre un documento que ya existe. -->
        <WorkflowActions
          v-if="tieneFlujo && doc.doc"
          class="mb-6"
          :document="doc.doc"
          @completed="doc.reload()"
        />

        <form class="sb-form-card space-y-5" @submit.prevent="save">
          <div v-for="f in visibleFields" :key="f.fieldname">
            <FieldInput
              v-model="values[f.fieldname]"
              :field="f"
              :read-only="Boolean(f.read_only)"
              :doctype="doctype"
              :docname="name"
            />
          </div>

          <div class="flex items-center gap-3 border-t border-borde pt-5">
            <Boton variante="primario" type="submit" :cargando="saving">
              {{ isNew ? 'Crear' : 'Guardar' }}
            </Boton>
            <span v-if="saved" class="text-sm text-exito">Guardado.</span>
            <Alerta v-if="saveError" :message="saveError.message" />
          </div>
        </form>
      </template>

      <!-- Conexiones (Document Links del meta): p.ej. Evidencia -> Trazabilidad -->
      <div v-if="!metaLoading && (meta?.links || []).length" class="sb-form-card mt-8 space-y-6">
        <DocConnections
          v-for="lnk in meta.links"
          :key="lnk.link_doctype + lnk.link_fieldname"
          :parent-doctype="doctype"
          :parent-name="name"
          :link="lnk"
        />
      </div>
    </div>
  </AreaScroll>
</template>
