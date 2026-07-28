<script setup>
/**
 * Menú desplegable. Envoltorio del `DropdownMenu` de shadcn-vue.
 *
 * Antes montaba las primitivas de reka-ui a mano con las animaciones escritas al
 * vuelo. Los suyos ya traen el juego completo de estados —entrada y SALIDA, y
 * el desplazamiento según el lado en que el menú acabe abriéndose— que yo había
 * puesto solo para `state=open`: al cerrarse, el mío desaparecía de golpe.
 *
 * Se conserva del original lo que sigue siendo doctrina de la casa (§6): escala
 * desde SU DISPARADOR, no desde el centro. Confundir un popover con un modal se
 * nota aunque nadie sepa decir por qué. Eso ya viene en su `DropdownMenuContent`
 * vía `--reka-dropdown-menu-content-transform-origin`.
 *
 * La API por `opciones` se mantiene: el AppShell la usa y no hay motivo para
 * obligar a componer seis componentes donde basta una lista.
 */
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

defineProps({
  opciones: { type: Array, default: () => [] }, // [{ label, icon, onClick }]
  alineacion: { type: String, default: 'end' },
})
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <slot />
    </DropdownMenuTrigger>
    <DropdownMenuContent
      :align="alineacion"
      :side-offset="6"
      class="min-w-48 rounded-xl"
    >
      <DropdownMenuItem
        v-for="o in opciones"
        :key="o.label"
        class="cursor-pointer rounded-lg px-3 py-2 text-sm"
        @select="o.onClick"
      >
        <component :is="o.icon" v-if="o.icon" :size="16" aria-hidden="true" />
        <span>{{ o.label }}</span>
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
