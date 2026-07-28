<script setup>
/**
 * Menú desplegable. Reemplaza al `Dropdown` de frappe-ui.
 *
 * Sobre reka-ui: foco atrapado, `Esc` cierra, navegación con flechas y cierre
 * al pulsar fuera vienen resueltos — no se rehacen a mano (estilo §6).
 *
 * Escala desde SU DISPARADOR, no desde el centro: eso es un popover, y
 * confundirlo con un modal se nota aunque nadie sepa decir por qué (§6).
 */
import {
  DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuPortal,
  DropdownMenuContent, DropdownMenuItem,
} from 'reka-ui'

defineProps({
  opciones: { type: Array, default: () => [] }, // [{ label, icon, onClick }]
  alineacion: { type: String, default: 'end' },
})
</script>

<template>
  <DropdownMenuRoot>
    <DropdownMenuTrigger as-child>
      <slot />
    </DropdownMenuTrigger>
    <DropdownMenuPortal>
      <DropdownMenuContent
        :align="alineacion"
        :side-offset="6"
        class="z-50 min-w-48 rounded-xl border border-borde bg-superficie p-1 shadow-xl
               origin-[var(--reka-dropdown-menu-content-transform-origin)]
               data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95
               duration-150 ease-out motion-reduce:animate-none"
      >
        <DropdownMenuItem
          v-for="o in opciones"
          :key="o.label"
          class="flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm text-tinta
                 data-[highlighted]:bg-superficie-2 data-[highlighted]:outline-none"
          @select="o.onClick"
        >
          <component :is="o.icon" v-if="o.icon" :size="16" aria-hidden="true" />
          <span>{{ o.label }}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenuPortal>
  </DropdownMenuRoot>
</template>
