<script setup>
/**
 * Botón de la casa. ENVOLTORIO del `Button` de shadcn-vue, no un reemplazo.
 *
 * Por qué envolver en vez de escribirlo entero (que es lo que había antes): el de
 * shadcn resuelve detalles que yo no tenía y que se olvidan uno por uno — ajusta
 * el padding cuando hay icono (`has-[>svg]:px-3`), dimensiona los SVG sin que
 * nadie lo pida, cubre `aria-invalid`, y es polimórfico por `Primitive`. Además,
 * al quedar intacto en `ui/button/`, un `shadcn-vue add` futuro lo actualiza con
 * las correcciones de aguas arriba.
 *
 * Y por qué no usarlo pelado: choca con el canon SciBack en cuatro puntos, que se
 * corrigen aquí SIN tocar su fichero.
 *
 *  · VARIANTES SEMÁNTICAS (estilo §3). Quien lo usa dice qué ES la acción, no de
 *    qué color la quiere; así un cambio de paleta no obliga a revisar pantallas.
 *  · RADIO `rounded-xl`. shadcn trae `rounded-md`; el canon fija xl por defecto
 *    en botones, campos y tarjetas.
 *  · ZONA TÁCTIL. El `default` de shadcn mide 36px de alto y WCAG 2.5.5 pide 44,
 *    así que el tamaño por defecto de la casa es `h-11`; los 36 quedan para `sm`,
 *    el compacto de tabla.
 *  · HUNDIDO AL PULSAR. Firma de SciBack (§7): sin él la UI no confirma que te
 *    oyó. shadcn no lo trae.
 */
import { computed, useAttrs } from 'vue'
import { RouterLink } from 'vue-router'
import { Loader } from 'reicon-vue'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const props = defineProps({
  variante: { type: String, default: 'secundario' }, // primario | secundario | peligro | fantasma
  tamano: { type: String, default: 'md' }, // sm | md
  cargando: { type: Boolean, default: false },
  deshabilitado: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
  route: { type: [Object, String], default: null },
})

// Única traducción entre la API de la casa y la de shadcn, en un solo sitio a
// propósito: si mañana shadcn renombra una variante, se arregla aquí y no en las
// 16 pantallas que usan el botón.
const VARIANTES = {
  primario: 'default',
  secundario: 'outline',
  peligro: 'destructive',
  fantasma: 'ghost',
}
const TAMANOS = { sm: 'sm', md: 'default' }

// Correcciones de la casa. Van por `class` porque `cn` (tailwind-merge) resuelve
// el conflicto a favor del llamador: ganan a las clases del componente sin
// necesidad de `!important`.
const CASA = [
  'rounded-xl',
  'active:scale-[0.97]',
  'transition-[transform,background-color,border-color,box-shadow] duration-150',
  'ease-[cubic-bezier(0.34,1.56,0.64,1)]',
  'motion-reduce:transition-none motion-reduce:active:scale-100',
]
const ALTO = { sm: 'h-9', md: 'h-11 px-4' }

defineOptions({ inheritAttrs: false })
const attrs = useAttrs()

const clases = computed(() => cn(CASA, ALTO[props.tamano] ?? ALTO.md, attrs.class))
const restoAttrs = computed(() => {
  const { class: _omitida, ...resto } = attrs
  return resto
})
const inerte = computed(() => props.deshabilitado || props.cargando)
const variant = computed(() => VARIANTES[props.variante] ?? 'outline')
const size = computed(() => TAMANOS[props.tamano] ?? 'default')
</script>

<template>
  <Button
    v-if="route && !inerte"
    v-bind="restoAttrs"
    :as="RouterLink"
    :to="route"
    :variant="variant"
    :size="size"
    :class="clases"
  >
    <Loader v-if="cargando" :size="16" class="animate-spin" aria-hidden="true" />
    <slot />
  </Button>
  <Button
    v-else
    v-bind="restoAttrs"
    :type="type"
    :disabled="inerte"
    :variant="variant"
    :size="size"
    :class="clases"
    :aria-busy="cargando || undefined"
  >
    <Loader v-if="cargando" :size="16" class="animate-spin" aria-hidden="true" />
    <slot />
  </Button>
</template>
