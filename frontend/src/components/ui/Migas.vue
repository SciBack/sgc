<script setup>
/** Ruta de navegación. Reemplaza al `Breadcrumbs` de frappe-ui.
 *  Expresa UBICACIÓN; el título de la página no la repite (estilo §3.1). */
import { AngleRight } from 'reicon-vue'

defineProps({ items: { type: Array, required: true } })
</script>

<template>
  <nav aria-label="Ruta de navegación">
    <ol class="flex flex-wrap items-center gap-1 text-sm">
      <li v-for="(item, i) in items" :key="i" class="flex items-center gap-1">
        <AngleRight v-if="i > 0" :size="14" class="text-tinta-tenue" aria-hidden="true" />
        <RouterLink
          v-if="item.route && i < items.length - 1"
          :to="item.route"
          class="rounded text-tinta-tenue transition-colors duration-150 hover:text-tinta focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color-mix(in_srgb,var(--color-marca-primaria-500)_40%,transparent)]"
        >{{ item.label }}</RouterLink>
        <span
          v-else
          :class="i === items.length - 1 ? 'font-medium text-tinta' : 'text-tinta-tenue'"
          :aria-current="i === items.length - 1 ? 'page' : undefined"
        >{{ item.label }}</span>
      </li>
    </ol>
  </nav>
</template>
