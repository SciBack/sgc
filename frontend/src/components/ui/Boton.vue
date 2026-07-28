<script setup>
/**
 * Botón de la casa. Reemplaza al `Button` de frappe-ui.
 *
 * Variantes SEMÁNTICAS (estilo SciBack §3), no visuales: quien lo usa dice qué
 * ES la acción, no de qué color la quiere. Así un cambio de paleta no obliga a
 * revisar cada pantalla.
 *
 * Absorbe `sb-primary-action` y `btn-press`, que antes se pegaban a mano en
 * cada uso — y por tanto se olvidaban. El hundido al pulsar es la firma de
 * SciBack (§7): sin él la UI no confirma que te oyó.
 */
import { computed, useAttrs } from 'vue'
import { cva } from 'class-variance-authority'
import { RouterLink } from 'vue-router'
import { Loader } from 'reicon-vue'
import { cn } from '@/lib/cn'

const props = defineProps({
  variante: { type: String, default: 'secundario' }, // primario | secundario | peligro | fantasma
  tamano: { type: String, default: 'md' }, // sm | md
  cargando: { type: Boolean, default: false },
  deshabilitado: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
  route: { type: [Object, String], default: null },
})

const estilos = cva(
  // `transform` y `opacity` son lo único que se anima: van en GPU (método §3).
  // La curva con rebote sutil da el «clic» físico.
  [
    'inline-flex items-center justify-center gap-2 rounded-xl border font-medium',
    'transition-[transform,background-color,border-color,box-shadow] duration-150',
    'ease-[cubic-bezier(0.34,1.56,0.64,1)]',
    'active:scale-[0.97]',
    'focus-visible:outline-none focus-visible:ring-[3px]',
    'focus-visible:ring-[color-mix(in_srgb,var(--color-marca-primaria-500)_25%,transparent)]',
    'disabled:pointer-events-none disabled:opacity-55',
    'motion-reduce:transition-none motion-reduce:active:scale-100',
  ],
  {
    variants: {
      variante: {
        primario:
          'border-marca-primaria-700 bg-marca-primaria-700 text-sobre-marca-primaria shadow-[0_5px_14px_-9px_color-mix(in_srgb,var(--color-marca-primaria-900)_72%,transparent)] hover:bg-marca-primaria-600',
        secundario: 'border-borde-fuerte bg-superficie text-tinta hover:bg-superficie-2',
        peligro: 'border-peligro bg-peligro text-sobre-marca-primaria hover:opacity-90',
        fantasma: 'border-transparent bg-transparent text-tinta-suave hover:bg-superficie-2',
      },
      tamano: {
        // 36px de alto en `sm` y 44px en `md`: el mínimo táctil de WCAG 2.5.5
        // se respeta en el tamaño por defecto, no en el compacto de tabla.
        sm: 'h-9 px-3 text-sm',
        md: 'h-11 px-4 text-sm',
      },
    },
    defaultVariants: { variante: 'secundario', tamano: 'md' },
  },
)

// `inheritAttrs: false` + merge explicito del `class` entrante. Sin esto Vue
// CONCATENA las dos listas de clases y el conflicto lo resuelve el orden en que
// Tailwind emitio el CSS, no quien escribe la pantalla: un `class="bg-white"`
// sobre variante="primario" salia azul o blanco segun el dia.
// Pasandolo por `cn` (tailwind-merge) gana siempre la del llamador, que es lo
// esperable — y por eso deja de hacer falta `!important` para sobreescribir.
defineOptions({ inheritAttrs: false })
const attrs = useAttrs()

const clases = computed(() =>
  cn(estilos({ variante: props.variante, tamano: props.tamano }), attrs.class),
)
const restoAttrs = computed(() => {
  const { class: _omitida, ...resto } = attrs
  return resto
})
const inerte = computed(() => props.deshabilitado || props.cargando)
</script>

<template>
  <RouterLink v-if="route && !inerte" v-bind="restoAttrs" :to="route" :class="clases">
    <Loader v-if="cargando" :size="16" class="animate-spin" aria-hidden="true" />
    <slot />
  </RouterLink>
  <button
    v-else
    v-bind="restoAttrs"
    :type="type"
    :disabled="inerte"
    :class="clases"
    :aria-busy="cargando || undefined"
  >
    <Loader v-if="cargando" :size="16" class="animate-spin" aria-hidden="true" />
    <slot />
  </button>
</template>
