<script setup>
import { ref, watch } from 'vue'
import { useCall } from 'frappe-ui'
import Boton from '@/components/ui/Boton.vue'
import Alerta from '@/components/ui/Alerta.vue'
import Campo from '@/components/ui/Campo.vue'
import EstadoBadge from '@/components/ui/EstadoBadge.vue'

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
      <span class="rounded-lg superficie-marca px-2 py-1 font-mono text-xs font-semibold ">
        {{ row.em_codigo }}
      </span>
      <div class="min-w-0 flex-1">
        <h3 class="font-display text-base font-semibold leading-5 text-tinta">{{ row.em_denominacion }}</h3>
        <div class="mt-2 flex flex-wrap items-center gap-2 text-xs text-tinta-tenue">
          <span>Nivel propuesto: <strong class="text-tinta">{{ row.nivel_propuesto || 'Pendiente' }}</strong></span>
          <span aria-hidden="true">·</span>
          <EstadoBadge :label="row.confirmado ? 'Confirmado' : (row.estado || 'Borrador')" :theme="row.confirmado ? 'green' : 'gray'" />
          <span v-if="row.nivel_sigla">Oficial: <strong class="text-tinta">{{ row.nivel_sigla }}</strong></span>
        </div>
      </div>
    </div>

    <div v-if="canConfirm" class="grid grid-cols-1 gap-4 sm:grid-cols-[11rem_1fr]">
      <label class="block">
        <span class="sb-field-label mb-1.5 block">Nivel oficial</span>
        <select
          v-model="nivelSigla"
          data-test="nivel-sigla"
          class="h-9 w-full rounded border border-borde-fuerte bg-superficie px-3 text-sm text-tinta outline-none focus:border-marca-primaria-500 focus:ring-2 focus:ring-marca-primaria-100"
        >
          <option value="" disabled>Seleccionar…</option>
          <option value="NL">NL · No logrado</option>
          <option value="L">L · Logrado</option>
          <option value="LP">LP · Logrado plenamente</option>
        </select>
      </label>
      <Campo type="textarea"
            :rows="3" label="Justificación" v-model="justificacion" />
    </div>

    <div v-if="canConfirm" class="mt-4 flex flex-wrap items-center gap-3 border-t border-borde pt-4">
      <Boton
        variante="primario"
        :cargando="confirmation.loading"
        :deshabilitado="!nivelSigla"
        @click="confirm"
      >
        {{ row.confirmado ? 'Actualizar confirmación' : 'Confirmar nivel' }}
      </Boton>
      <span v-if="saved" class="text-sm text-exito">Nivel confirmado.</span>
      <Alerta v-if="confirmation.error" :message="confirmation.error.message" />
    </div>
    <p v-else class="mt-4 rounded-lg bg-superficie-2 px-3 py-2 text-xs text-tinta-suave">
      La confirmación oficial corresponde a DPGC o al Responsable de Calidad del Programa.
    </p>

    <div class="mt-4 space-y-2">
      <slot name="criterios" />
    </div>
  </div>
</template>
