<script setup>
/** Área con scroll. Reemplaza al `ScrollArea` de frappe-ui.
 *
 *  Se apoya en reka-ui (la primitiva del stack canónico para Vue): el foco, el
 *  teclado y el arrastre de la barra ya vienen resueltos, sin imponer estética.
 */
import { ScrollAreaRoot, ScrollAreaViewport, ScrollAreaScrollbar, ScrollAreaThumb } from 'reka-ui'
import { cn } from '@/lib/utils'

defineProps({ viewportClass: { type: String, default: '' } })
</script>

<template>
  <ScrollAreaRoot :class="cn('relative overflow-hidden', $attrs.class)" type="hover">
    <ScrollAreaViewport :class="cn('h-full w-full', viewportClass)">
      <slot />
    </ScrollAreaViewport>
    <ScrollAreaScrollbar
      orientation="vertical"
      class="flex w-2 touch-none select-none p-0.5 transition-colors duration-150"
    >
      <ScrollAreaThumb class="flex-1 rounded-full bg-borde-fuerte" />
    </ScrollAreaScrollbar>
  </ScrollAreaRoot>
</template>
