<script setup>
/** Chip de estado. Envoltorio del `Badge` de shadcn-vue.
 *
 *  Estilo §3: SIEMPRE con texto, nunca color solo. El color acompaña al
 *  significado, no lo sustituye — la identidad de un estado no puede depender
 *  únicamente del tono (método §2.3).
 *
 *  Del suyo llegan detalles que el `<span>` pelado no tenía: dimensiona los SVG
 *  interiores (`[&>svg]:size-3`), impide que el chip se encoja o parta línea
 *  (`w-fit whitespace-nowrap shrink-0`) y trae anillo de foco para cuando el
 *  chip sea un enlace. Sus cuatro variantes son de MARCA, no de estado, así que
 *  se usa `outline` como base neutra y los tonos los pone la casa.
 *
 *  Los temas siguen nombrándose por COLOR (`green`, `blue`…) porque es la API
 *  que ya usaban las pantallas; se traducen aquí a tokens semánticos para no
 *  tener que tocar cada llamada. Lo nuevo debería pasar `tono` semántico.
 */
import { computed } from 'vue'
import { Badge } from '@/components/ui/badge'
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
    props.size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
    TONOS[t] ?? TONOS.neutro,
  )
})
</script>

<template>
  <Badge variant="outline" :class="clases"><slot>{{ label }}</slot></Badge>
</template>
