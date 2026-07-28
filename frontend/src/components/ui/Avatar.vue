<script setup>
/** Avatar con iniciales. Reemplaza al `Avatar` de frappe-ui.
 *  Sin imagen: las iniciales son el contenido, y el `title` da el nombre completo
 *  a quien use lector de pantalla o pase el cursor. */
import { computed } from 'vue'
import { cn } from '@/lib/cn'

const props = defineProps({
  nombre: { type: String, default: '' },
  tamano: { type: String, default: 'sm' }, // sm | lg
})

const iniciales = computed(() =>
  props.nombre.split(/[\s.@_-]+/).filter(Boolean).slice(0, 2)
    .map((p) => p[0]).join('').toUpperCase(),
)
</script>

<template>
  <span
    :title="nombre"
    :class="cn(
      'inline-flex shrink-0 items-center justify-center rounded-full font-semibold',
      'bg-marca-primaria-600 text-sobre-marca-primaria',
      tamano === 'lg' ? 'size-9 text-sm' : 'size-7 text-xs',
    )"
  >{{ iniciales }}</span>
</template>
