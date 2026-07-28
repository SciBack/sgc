<script setup>
/**
 * Área con scroll. Envoltorio del `ScrollArea` de shadcn-vue.
 *
 * Antes montaba las primitivas de reka-ui a mano. El de shadcn añade dos cosas
 * que no se echan de menos hasta que alguien navega con teclado: un anillo de
 * foco en el viewport —un área desplazable ES enfocable, y sin señal visible no
 * se sabe qué se mueve con las flechas— y el `ScrollAreaCorner`, que tapa el
 * hueco muerto cuando coinciden las dos barras.
 *
 * `viewportClass` se mantiene porque el AppShell lo usa para el padding interno
 * del lateral; shadcn no expone esa ranura, así que va en un div propio dentro.
 */
import { ScrollArea } from '@/components/ui/scroll-area'

defineProps({ viewportClass: { type: String, default: '' } })
</script>

<template>
  <ScrollArea type="hover" :class="$attrs.class">
    <div :class="viewportClass">
      <slot />
    </div>
  </ScrollArea>
</template>
