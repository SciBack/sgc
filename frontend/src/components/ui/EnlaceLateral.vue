<script setup>
/**
 * Entrada del menú lateral. Reemplaza al `SidebarItem` de frappe-ui.
 *
 * Al ser marcado propio desaparecen los `:deep([data-slot='sidebar-item'])` con
 * `!important` que hacían falta para revestir el componente ajeno. Ese es el
 * argumento del estilo §1 para shadcn: el aspecto lo ponen nuestros tokens, no
 * se pelea contra los de la librería.
 *
 * Estado activo del estilo §3.1: fondo blanco al 14% + filete de 2px de la marca
 * secundaria a la izquierda. Reconocible sin ser estridente; los inactivos
 * quedan al 72%.
 *
 * `isExactActive`, NO `isActive`. Detectado mirando la pantalla renderizada: con
 * `isActive`, «Inicio» —que apunta a `/sgc/`— salía resaltado en TODAS las
 * páginas, porque su ruta es ancestro de cualquier otra. Se veían dos entradas
 * encendidas a la vez y, peor, había dos `aria-current="page"` en el mismo
 * documento: un lector de pantalla anuncia dos «páginas actuales».
 * Todas las entradas de este lateral apuntan a rutas hoja, así que la
 * coincidencia exacta es la correcta para todas.
 */
import { cn } from '@/lib/utils'

defineProps({ to: { type: [Object, String], required: true } })
</script>

<template>
  <RouterLink
    v-slot="{ isExactActive: isActive, href, navigate }"
    :to="to"
    custom
  >
    <a
      :href="href"
      :aria-current="isActive ? 'page' : undefined"
      :class="cn(
        'flex h-8 items-center gap-2 rounded-lg px-2 text-sm',
        'transition-colors duration-150',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color-mix(in_srgb,var(--color-marca-secundaria-500)_60%,transparent)]',
        isActive
          ? 'bg-white/[0.14] font-medium text-white shadow-[inset_2px_0_0_var(--color-marca-secundaria-500)]'
          : 'text-white/[0.72] hover:bg-white/10 hover:text-white',
      )"
      @click="navigate"
    >
      <slot name="icono" />
      <span class="flex-1 truncate"><slot /></span>
    </a>
  </RouterLink>
</template>
