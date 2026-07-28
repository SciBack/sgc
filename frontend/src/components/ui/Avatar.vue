<script setup>
/**
 * Avatar con iniciales. Envoltorio del `Avatar` de shadcn-vue.
 *
 * Hoy el SGC no tiene fotos de perfil, así que solo se pinta el fallback. Se
 * envuelve igualmente porque `AvatarRoot`/`AvatarFallback` de reka-ui ya traen
 * la máquina de estados de carga de imagen: cuando Frappe empiece a servir
 * avatares basta con añadir `<AvatarImage>` y las iniciales pasan a ser el
 * respaldo real, sin el parpadeo de una imagen a medio cargar.
 *
 * De la casa: color de marca —el gris neutro de shadcn no identifica a nadie— y
 * el `title` con el nombre completo, que es lo que lee quien pasa el cursor.
 */
import { computed } from 'vue'
import { Avatar as AvatarBase, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'

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
  <AvatarBase
    :title="nombre"
    :class="cn(tamano === 'lg' ? 'size-9' : 'size-7')"
  >
    <AvatarFallback
      :class="cn(
        'bg-marca-primaria-600 font-semibold text-sobre-marca-primaria',
        tamano === 'lg' ? 'text-sm' : 'text-xs',
      )"
    >{{ iniciales }}</AvatarFallback>
  </AvatarBase>
</template>
