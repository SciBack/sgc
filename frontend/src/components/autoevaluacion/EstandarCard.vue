<script setup>
import { ref, watch } from 'vue'
import { Badge, Button, ErrorMessage, FormControl, useCall } from 'frappe-ui'

const props = defineProps({
  row: { type: Object, required: true },
  autoevaluacion: { type: String, required: true },
  canConfirm: { type: Boolean, default: false },
})

const emit = defineEmits(['updated'])

const nivelSigla = ref(props.row.nivel_sigla || props.row.nivel_propuesto || '')
const justificacion = ref(props.row.justificacion || '')
const saved = ref(false)

watch(
  () => [props.row.nivel_sigla, props.row.nivel_propuesto, props.row.justificacion],
  ([oficial, propuesto, comentario]) => {
    nivelSigla.value = oficial || propuesto || ''
    justificacion.value = comentario || ''
  },
)

const confirmation = useCall({
  url: '/api/v2/method/sgc.confirmacion.confirmar_nivel',
  method: 'POST',
  immediate: false,
})

async function confirm() {
  if (!nivelSigla.value || confirmation.loading) return
  saved.value = false
  const result = await confirmation.submit({
    autoevaluacion: props.autoevaluacion,
    estandar: props.row.elemento_marco,
    nivel_sigla: nivelSigla.value,
    comentario: justificacion.value.trim() || null,
  })
  if (!result || confirmation.error) return
  saved.value = true
  emit('updated', result)
}
</script>

<template>
  <div class="sb-card p-5">
    <div class="mb-4 flex items-start gap-3">
      <span class="rounded-lg bg-marca-primaria-50 px-2 py-1 font-mono text-xs font-semibold text-marca-primaria-700">
        {{ row.em_codigo }}
      </span>
      <div class="min-w-0 flex-1">
        <h3 class="font-display text-base font-semibold leading-5 text-ink-gray-9">{{ row.em_denominacion }}</h3>
        <div class="mt-2 flex flex-wrap items-center gap-2 text-p-xs text-ink-gray-5">
          <span>Nivel propuesto: <strong class="text-ink-gray-8">{{ row.nivel_propuesto || 'Pendiente' }}</strong></span>
          <span aria-hidden="true">·</span>
          <Badge :label="row.confirmado ? 'Confirmado' : (row.estado || 'Borrador')" :theme="row.confirmado ? 'green' : 'gray'" variant="subtle" />
          <span v-if="row.nivel_sigla">Oficial: <strong class="text-ink-gray-8">{{ row.nivel_sigla }}</strong></span>
        </div>
      </div>
    </div>

    <div v-if="canConfirm" class="grid grid-cols-1 gap-4 sm:grid-cols-[11rem_1fr]">
      <label class="block">
        <span class="sb-field-label mb-1.5 block">Nivel oficial</span>
        <select
          v-model="nivelSigla"
          data-test="nivel-sigla"
          class="h-9 w-full rounded border border-outline-gray-2 bg-surface-white px-3 text-p-sm text-ink-gray-8 outline-none focus:border-marca-primaria-500 focus:ring-2 focus:ring-marca-primaria-100"
        >
          <option value="" disabled>Seleccionar…</option>
          <option value="NL">NL · No logrado</option>
          <option value="L">L · Logrado</option>
          <option value="LP">LP · Logrado plenamente</option>
        </select>
      </label>
      <FormControl type="textarea" variant="outline" label="Justificación" v-model="justificacion" :rows="3" />
    </div>

    <div v-if="canConfirm" class="mt-4 flex flex-wrap items-center gap-3 border-t border-outline-gray-1 pt-4">
      <Button
        variant="solid"
        class="sb-primary-action btn-press"
        :loading="confirmation.loading"
        :disabled="!nivelSigla"
        @click="confirm"
      >
        {{ row.confirmado ? 'Actualizar confirmación' : 'Confirmar nivel' }}
      </Button>
      <span v-if="saved" class="text-p-sm text-ink-green-6">Nivel confirmado.</span>
      <ErrorMessage v-if="confirmation.error" :message="confirmation.error.message" />
    </div>
    <p v-else class="mt-4 rounded-lg bg-surface-gray-1 px-3 py-2 text-p-xs text-ink-gray-6">
      La confirmación oficial corresponde a DPGC o al Responsable de Calidad del Programa.
    </p>

    <div class="mt-4 space-y-2">
      <slot name="criterios" />
    </div>
  </div>
</template>
