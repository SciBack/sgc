<script setup>
/** Espera. Propio a propósito: el registro tiene `spinner`, pero NO es mejor.
 *
 *  Se trajo y se descartó tras leerlo: su `Spinner` es un icono de lucide con
 *  `animate-spin` y nada más. No trae texto ni `aria-live`, así que quien use
 *  lector de pantalla no se entera de que hay una espera en curso; y obligaría a
 *  mantener un segundo pack de iconos solo para eso. Adoptarlo habría sido
 *  cambiar algo mejor por algo peor por seguir la forma.
 *
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
