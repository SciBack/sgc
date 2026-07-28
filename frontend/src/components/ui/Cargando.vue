<script setup>
/** Espera. Reemplaza al `LoadingText` de frappe-ui.
 *  Estilo §3: nunca un salto en seco. El spinner gira rápido a propósito —
 *  un spinner veloz hace percibir la carga como más corta con el mismo tiempo real. */
import { Loader } from 'reicon-vue'

defineProps({ texto: { type: String, default: 'Cargando…' } })
</script>

<template>
  <p class="flex items-center gap-2 py-6 text-sm text-tinta-tenue" role="status" aria-live="polite">
    <Loader :size="16" class="animate-spin motion-reduce:animate-none" aria-hidden="true" />
    <span>{{ texto }}</span>
  </p>
</template>
