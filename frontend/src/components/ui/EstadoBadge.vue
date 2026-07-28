<script setup>
/** Chip de estado. Reemplaza al `Badge` de frappe-ui.
 *
 *  Estilo §3: SIEMPRE con texto, nunca color solo. El color acompaña al
 *  significado, no lo sustituye — la identidad de un estado no puede depender
 *  únicamente del tono (método §2.3).
 *
 *  Los temas siguen nombrándose por COLOR (`green`, `blue`…) porque es la API
 *  que ya usaban las pantallas; se traducen aquí a tokens semánticos para no
 *  tener que tocar cada llamada. Lo nuevo debería pasar `tono` semántico.
 */
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  label: { type: String, default: '' },
  theme: { type: String, default: 'gray' },
  tono: { type: String, default: null }, // neutro | exito | info | aviso | peligro
  size: { type: String, default: 'sm' },
})

const DE_COLOR_A_TONO = {
  gray: 'neutro', green: 'exito', blue: 'info',
  orange: 'aviso', amber: 'aviso', yellow: 'aviso', red: 'peligro',
}
const TONOS = {
  neutro: 'border-borde bg-superficie-2 text-tinta-suave',
  exito: 'border-exito-tenue bg-exito-tenue text-exito',
  info: 'border-borde bg-info-tenue text-info',
  aviso: 'border-aviso-tenue bg-aviso-tenue text-aviso',
  peligro: 'border-peligro-tenue bg-peligro-tenue text-peligro',
}
const clases = computed(() => {
  const t = props.tono ?? DE_COLOR_A_TONO[props.theme] ?? 'neutro'
  return cn(
    'inline-flex items-center gap-1 rounded-full border font-medium',
    props.size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
    TONOS[t] ?? TONOS.neutro,
  )
})
</script>

<template>
  <span :class="clases"><slot>{{ label }}</slot></span>
</template>
