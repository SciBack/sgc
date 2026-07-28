<script setup>
/** Mensaje inline de estado. Reemplaza al `ErrorMessage` de frappe-ui.
 *  Estilo §3: icono + texto, nunca color solo — un usuario con daltonismo debe
 *  poder distinguir un error de un aviso sin depender del tono. */
import { computed } from 'vue'
import { AlertCircle, AlertTriangle, CheckCircle, InfoCircle } from 'reicon-vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  message: { type: String, default: '' },
  tono: { type: String, default: 'error' }, // error | aviso | exito | info
})

const CONFIG = {
  error: { icono: AlertCircle, clases: 'border-peligro-tenue bg-peligro-tenue text-peligro', rol: 'alert' },
  aviso: { icono: AlertTriangle, clases: 'border-aviso-tenue bg-aviso-tenue text-aviso', rol: 'status' },
  exito: { icono: CheckCircle, clases: 'border-exito-tenue bg-exito-tenue text-exito', rol: 'status' },
  info: { icono: InfoCircle, clases: 'border-borde bg-info-tenue text-info', rol: 'status' },
}
const cfg = computed(() => CONFIG[props.tono] ?? CONFIG.error)
</script>

<template>
  <p
    v-if="message || $slots.default"
    :role="cfg.rol"
    :class="cn('flex items-start gap-2 rounded-xl border px-3 py-2 text-sm', cfg.clases)"
  >
    <component :is="cfg.icono" :size="16" class="mt-0.5 shrink-0" aria-hidden="true" />
    <span><slot>{{ message }}</slot></span>
  </p>
</template>
