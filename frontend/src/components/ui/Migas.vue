<script setup>
/**
 * Ruta de navegación. Envoltorio del `Breadcrumb` de shadcn-vue.
 * Expresa UBICACIÓN; el título de la página no la repite (estilo §3.1).
 *
 * Lo que resuelve el suyo y mi bucle no: `BreadcrumbPage` marca el último tramo
 * con `role="link" aria-disabled aria-current="page"`, que es la forma correcta
 * de decir «estás aquí» —yo ponía `aria-current` sobre un `<span>` mudo—, y el
 * separador va con `role="presentation" aria-hidden`, para que el lector de
 * pantalla no lea un «mayor que» entre cada nivel.
 *
 * De la casa: el separador es el `AngleRight` de reicon, no el chevron de lucide
 * que trae el componente por defecto.
 */
import { AngleRight } from 'reicon-vue'
import {
  Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList,
  BreadcrumbPage, BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import { RouterLink } from 'vue-router'

defineProps({ items: { type: Array, required: true } })
</script>

<template>
  <Breadcrumb>
    <BreadcrumbList class="gap-1 text-sm sm:gap-1">
      <template v-for="(item, i) in items" :key="i">
        <BreadcrumbSeparator v-if="i > 0" class="text-tinta-tenue">
          <AngleRight :size="14" aria-hidden="true" />
        </BreadcrumbSeparator>
        <BreadcrumbItem>
          <BreadcrumbLink
            v-if="item.route && i < items.length - 1"
            :as="RouterLink"
            :to="item.route"
            class="text-tinta-tenue hover:text-tinta"
          >{{ item.label }}</BreadcrumbLink>
          <BreadcrumbPage
            v-else-if="i === items.length - 1"
            class="font-medium text-tinta"
          >{{ item.label }}</BreadcrumbPage>
          <span v-else class="text-tinta-tenue">{{ item.label }}</span>
        </BreadcrumbItem>
      </template>
    </BreadcrumbList>
  </Breadcrumb>
</template>
