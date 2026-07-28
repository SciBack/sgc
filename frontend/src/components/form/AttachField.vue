<script setup>
import { computed } from 'vue'
import { FileUploader } from 'frappe-ui'
import { DocText, Loader, Upload, X } from 'reicon-vue'

// Control de archivo (fieldtype Attach / Attach Image) para la SPA.
// Sube vía el endpoint nativo de Frappe (FileUploader) y guarda el file_url
// en el campo. Frappe re-vincula el File al documento al guardarlo.
const props = defineProps({
  field: { type: Object, required: true },
  doctype: { type: String, default: '' },
  docname: { type: String, default: '' },
  readOnly: { type: Boolean, default: false },
})

const value = defineModel({ default: null })

const label = computed(() => props.field.label || props.field.fieldname)
const isImage = computed(() => props.field.fieldtype === 'Attach Image')

const fileName = computed(() => {
  if (!value.value) return ''
  const base = String(value.value).split('/').pop() || ''
  try {
    return decodeURIComponent(base)
  } catch {
    return base
  }
})

// doctype/fieldname permiten que Frappe adjunte el archivo al documento; en un
// registro nuevo aún no hay docname, así que sube privado y se vincula al guardar.
const uploadArgs = computed(() => {
  const args = { private: true, fieldname: props.field.fieldname }
  if (props.doctype) args.doctype = props.doctype
  if (props.docname && props.docname !== 'new') args.docname = props.docname
  return args
})

const accept = computed(() => (isImage.value ? 'image/*' : undefined))

function onSuccess(fileDoc) {
  value.value = fileDoc?.file_url || null
}
</script>

<template>
  <div class="space-y-1.5">
    <label class="sb-field-label block">{{ label }}</label>

    <!-- Con archivo: tarjeta con vista/descarga y (si editable) quitar -->
    <div v-if="value" class="attach-card flex items-center gap-3 rounded-xl border border-borde-fuerte bg-superficie-2 p-3">
      <img
        v-if="isImage"
        :src="value"
        alt=""
        class="size-10 shrink-0 rounded object-cover"
      />
      <span
        v-else
        class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-marca-primaria-50 text-marca-primaria-700"
        aria-hidden="true"
      >
        <DocText :size="20" />
      </span>

      <a
        :href="value"
        target="_blank"
        rel="noopener"
        class="min-w-0 flex-1 truncate text-sm text-tinta hover:text-tinta hover:underline"
        :title="fileName"
      >
        {{ fileName }}
      </a>

      <button
        v-if="!readOnly"
        type="button"
        class="attach-remove flex size-7 shrink-0 items-center justify-center rounded text-tinta-tenue hover:bg-superficie-3 hover:text-tinta"
        title="Quitar archivo"
        @click="value = null"
      >
        <X :size="16" aria-hidden="true" />
      </button>
    </div>

    <!-- Vacío + editable: zona de carga -->
    <FileUploader
      v-else-if="!readOnly"
      :file-types="accept"
      :upload-args="uploadArgs"
      @success="onSuccess"
    >
      <template #default="{ uploading, progress, openFileSelector }">
        <button
          type="button"
        class="attach-drop flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-borde-fuerte bg-superficie px-4 py-4 text-sm font-medium text-tinta-suave"
          :disabled="uploading"
          @click="openFileSelector"
        >
          <template v-if="uploading">
            <Loader :size="16" class="animate-spin" aria-hidden="true" />
            <span>Subiendo {{ progress }}%</span>
          </template>
          <template v-else>
            <Upload :size="16" aria-hidden="true" />
            <span>{{ isImage ? 'Subir imagen' : 'Subir archivo' }}</span>
          </template>
        </button>
      </template>
    </FileUploader>

    <!-- Vacío + solo lectura -->
    <p v-else class="text-sm text-tinta-tenue">Sin archivo.</p>
  </div>
</template>

<style scoped>
/* Curva ease-out fuerte: da respuesta inmediata al aparecer/presionar. */
.attach-card {
  transition: opacity 200ms cubic-bezier(0.23, 1, 0.32, 1),
    transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
@starting-style {
  .attach-card {
    opacity: 0;
    transform: translateY(4px);
  }
}

/* La zona de carga y el botón quitar responden al hover y al press. */
.attach-drop,
.attach-remove {
  transition: background-color 150ms ease, border-color 150ms ease,
    color 150ms ease, transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
@media (hover: hover) and (pointer: fine) {
  .attach-drop:hover:not(:disabled) {
    border-color: var(--color-borde-fuerte);
    background-color: var(--color-superficie-2);
  }
}
.attach-drop:active:not(:disabled) {
  transform: scale(0.99);
}
.attach-remove:active {
  transform: scale(0.94);
}

@media (prefers-reduced-motion: reduce) {
  .attach-card,
  .attach-drop,
  .attach-remove {
    transition-property: opacity, background-color, border-color, color;
  }
}
</style>
