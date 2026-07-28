<script setup>
/**
 * Mensaje inline de estado. Envoltorio del `Alert` de shadcn-vue.
 *
 * Del suyo se aprovecha la REJILLA: `has-[>svg]:grid-cols-[...]` da al icono su
 * propia columna, así que un texto de dos líneas se alinea con la primera en vez
 * de meterse debajo del icono. Con el `flex` de antes eso había que corregirlo a
 * mano, y solo se notaba con mensajes largos.
 *
 * Lo que pone la casa, porque shadcn solo trae `default` y `destructive`:
 *  · CUATRO TONOS SEMÁNTICOS (error/aviso/exito/info). El canon los define como
 *    tinta sobre superficie tenue, derivada con `color-mix` en sciback-core.
 *  · ICONO SIEMPRE, nunca color solo (estilo §3): quien no distingue rojo de
 *    verde tiene que poder separar un error de un aviso.
 *  · `role` por tono: `alert` interrumpe al lector de pantalla y eso solo se
 *    justifica en un error; los demás son `status`.
 */
import { computed } from 'vue'
import { AlertCircle, AlertTriangle, CheckCircle, InfoCircle } from 'reicon-vue'
import { Alert, AlertDescription } from '@/components/ui/alert'
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
  <Alert
    v-if="message || $slots.default"
    :role="cfg.rol"
    :class="cn('rounded-xl', cfg.clases)"
  >
    <component :is="cfg.icono" :size="16" aria-hidden="true" />
    <AlertDescription class="text-current">
      <slot>{{ message }}</slot>
    </AlertDescription>
  </Alert>
</template>
