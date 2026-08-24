<script setup>
/**
 * Pila de avisos efímeros, abajo a la derecha. Se monta UNA vez, en el shell.
 *
 * Estilo §3: color nunca solo — cada tono lleva su icono, para quien no
 * distingue verde de rojo. `aria-live="polite"` para que un lector de pantalla
 * los anuncie sin interrumpir lo que la persona esté haciendo; un error de
 * verdad ya se muestra además inline, junto al campo que lo provocó.
 */
import { AlertCircle, AlertTriangle, CheckCircle, CloseCircle, InfoCircle } from 'reicon-vue'
import { avisos, cerrarAviso } from '@/composables/useAvisos'

const CONFIG = {
  exito: { icono: CheckCircle, clases: 'border-exito-tenue bg-exito-tenue text-exito' },
  info: { icono: InfoCircle, clases: 'border-borde bg-info-tenue text-info' },
  aviso: { icono: AlertTriangle, clases: 'border-aviso-tenue bg-aviso-tenue text-aviso' },
  error: { icono: AlertCircle, clases: 'border-peligro-tenue bg-peligro-tenue text-peligro' },
}
</script>

<template>
  <div
    class="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2"
    aria-live="polite"
    aria-atomic="false"
  >
    <TransitionGroup name="aviso">
      <div
        v-for="a in avisos"
        :key="a.id"
        class="pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 shadow-lg"
        :class="(CONFIG[a.tono] ?? CONFIG.info).clases"
        role="status"
      >
        <component
          :is="(CONFIG[a.tono] ?? CONFIG.info).icono"
          :size="18"
          class="mt-0.5 shrink-0"
          aria-hidden="true"
        />
        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold">{{ a.mensaje }}</p>
          <p v-if="a.detalle" class="mt-0.5 text-sm opacity-90">{{ a.detalle }}</p>
        </div>
        <button
          type="button"
          class="shrink-0 rounded p-0.5 opacity-60 transition-opacity hover:opacity-100"
          aria-label="Cerrar aviso"
          @click="cerrarAviso(a.id)"
        >
          <CloseCircle :size="14" aria-hidden="true" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.aviso-enter-active,
.aviso-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.aviso-enter-from {
  opacity: 0;
  transform: translateY(0.5rem);
}
.aviso-leave-to {
  opacity: 0;
  transform: translateX(1rem);
}
</style>
