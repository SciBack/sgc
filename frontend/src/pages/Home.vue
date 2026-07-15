<script setup>
import { computed } from 'vue'
import { ScrollArea, useCall } from 'frappe-ui'
import { useRouter } from 'vue-router'

const router = useRouter()

// Payload operativo del backend (sgc.home_dashboard.resumen_inicio): pendientes
// reales + estado de la autoevaluación activa.
const panel = useCall({
  url: '/api/v2/method/sgc.home_dashboard.resumen_inicio',
  cacheKey: 'home-resumen',
})

const autoevals = computed(() => panel.data?.autoevaluaciones || [])
const programasTotal = computed(() => panel.data?.programas_total || 0)
const pendientes = computed(() => panel.data?.pendientes || [])
const totalAtencion = computed(() => pendientes.value.reduce((n, p) => n + (p.valor || 0), 0))

function avanceDe(ae) {
  return Math.round(Number(ae?.avance_pct || 0))
}

function abrirAutoeval(ae) {
  router.push({ name: 'AutoevaluacionDetalle', params: { name: ae.name } })
}

// Tono de cada tarjeta de pendiente: si no hay nada, se muestra en calma
// (verde "al día"); si hay, rojo/ámbar según severidad.
function tono(p) {
  if (!p.valor) return { card: 'border-outline-gray-1', num: 'text-ink-gray-4', chip: 'bg-surface-gray-2 text-ink-gray-5', al_dia: true }
  if (p.tono === 'rojo') return { card: 'border-outline-red-1 bg-surface-red-1', num: 'text-ink-red-5', chip: 'bg-surface-red-2 text-ink-red-6' }
  return { card: 'border-outline-amber-1 bg-surface-amber-1', num: 'text-ink-amber-6', chip: 'bg-surface-amber-2 text-ink-amber-7' }
}

function irA(doctype) {
  router.push({ name: 'DoctypeList', params: { doctype } })
}

const accesos = [
  { label: 'Autoevaluación', icon: 'lucide-clipboard-check', doctype: 'Autoevaluacion' },
  { label: 'Cargar evidencia', icon: 'lucide-paperclip', doctype: 'Evidencia', nuevo: true },
  { label: 'Diagnóstico CBC', icon: 'lucide-shield-check', doctype: 'Informe Cumplimiento' },
  { label: 'Registrar hallazgo', icon: 'lucide-flag', doctype: 'Hallazgo', nuevo: true },
]

function abrirAcceso(a) {
  router.push({ name: 'DoctypeList', params: { doctype: a.doctype } })
}
</script>

<template>
  <ScrollArea class="min-h-0 flex-1">
    <div class="mx-auto max-w-5xl px-5 py-6 sm:px-8">
      <!-- Encabezado -->
      <div class="mb-5">
        <div class="text-xs font-semibold uppercase tracking-wide text-upeu-navy opacity-75">
          Universidad Peruana Unión · Dirección de Gestión de la Calidad
        </div>
        <h1 class="mt-1 font-display text-3xl font-bold tracking-tight text-upeu-navy">Inicio</h1>
      </div>

      <!-- Autoevaluaciones (multi-programa: 1..22 de la UPeU) -->
      <section class="mb-8">
        <div class="mb-3 flex flex-wrap items-center gap-2">
          <h2 class="text-lg font-semibold text-ink-gray-9">Autoevaluaciones</h2>
          <span
            v-if="!panel.loading && programasTotal"
            class="rounded-full bg-upeu-navy-050 px-2.5 py-0.5 text-xs font-semibold text-upeu-navy"
          >
            {{ autoevals.length }} de {{ programasTotal }} programas iniciados
          </span>
          <button
            class="ml-auto text-p-sm font-medium text-upeu-navy transition-opacity hover:opacity-70"
            @click="irA('Autoevaluacion')"
          >
            Ver todas →
          </button>
        </div>

        <div v-if="panel.loading" class="space-y-3">
          <div v-for="i in 2" :key="i" class="h-28 animate-pulse rounded-xl border border-outline-gray-1 bg-surface-gray-1" />
        </div>

        <div
          v-else-if="!autoevals.length"
          class="rounded-xl border border-dashed border-outline-gray-2 bg-surface-gray-1 p-6 text-center"
        >
          <p class="text-p-base font-medium text-ink-gray-7">Aún no hay autoevaluaciones iniciadas.</p>
          <p class="mt-1 text-p-sm text-ink-gray-5">
            Los {{ programasTotal }} programas de la UPeU están configurados; crea la primera desde Autoevaluación.
          </p>
        </div>

        <div v-else class="grid gap-3 sm:grid-cols-2">
          <button
            v-for="ae in autoevals"
            :key="ae.name"
            class="group flex flex-col rounded-xl border border-outline-gray-1 bg-gradient-to-b from-upeu-navy-050 to-surface-base p-5 text-left transition-[transform,box-shadow,border-color] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] hover:-translate-y-0.5 hover:border-upeu-navy/25 hover:shadow-md active:scale-[0.99]"
            @click="abrirAutoeval(ae)"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <h3 class="truncate font-display text-lg font-bold text-upeu-navy">
                  {{ ae.programa_sede || ae.titulo || ae.name }}
                </h3>
                <div class="mt-0.5 truncate text-p-xs text-ink-gray-5">
                  {{ ae.periodo_academico }} · {{ ae.marco_normativo }}
                </div>
              </div>
              <span class="shrink-0 rounded-full bg-surface-gray-2 px-2 py-0.5 text-xs font-medium text-ink-gray-6">
                {{ ae.estado }}
              </span>
            </div>

            <div class="mt-4">
              <div class="mb-1 flex items-baseline justify-between">
                <span class="text-p-xs font-medium text-ink-gray-6">Avance</span>
                <span class="font-display text-base font-bold text-upeu-navy">{{ avanceDe(ae) }}%</span>
              </div>
              <div class="h-2 w-full overflow-hidden rounded-full bg-surface-gray-3">
                <div
                  class="h-full rounded-full bg-upeu-navy transition-[width] duration-500 ease-[cubic-bezier(0.23,1,0.32,1)]"
                  :style="{ width: avanceDe(ae) + '%' }"
                />
              </div>
              <div class="mt-1.5 text-p-xs text-ink-gray-5">
                {{ ae.criterios_valorados }} de {{ ae.criterios_total }} criterios
                <template v-if="ae.criterios_pendientes">
                  · <b class="text-ink-amber-6">{{ ae.criterios_pendientes }} sin valorar</b>
                </template>
              </div>
            </div>
          </button>
        </div>
      </section>

      <!-- Requiere atención -->
      <section class="mb-8">
        <div class="mb-3 flex items-center gap-2">
          <h2 class="text-lg font-semibold text-ink-gray-9">Requiere atención</h2>
          <span
            v-if="!panel.loading"
            class="rounded-full px-2 py-0.5 text-xs font-semibold"
            :class="totalAtencion ? 'bg-surface-amber-2 text-ink-amber-7' : 'bg-surface-green-2 text-ink-green-6'"
          >
            {{ totalAtencion ? `${totalAtencion} pendientes` : 'Todo al día' }}
          </span>
        </div>

        <div v-if="panel.loading" class="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div v-for="i in 6" :key="i" class="h-24 animate-pulse rounded-lg border border-outline-gray-1 bg-surface-gray-1" />
        </div>

        <div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <button
            v-for="p in pendientes"
            :key="p.clave"
            class="group flex flex-col items-start rounded-lg border p-4 text-left transition-[transform,box-shadow,border-color] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] hover:-translate-y-0.5 hover:shadow-md active:scale-[0.99]"
            :class="tono(p).card"
            @click="irA(p.doctype)"
          >
            <div class="flex w-full items-center justify-between">
              <span class="font-display text-3xl font-bold" :class="tono(p).num">{{ p.valor }}</span>
              <span
                v-if="tono(p).al_dia"
                class="lucide-check size-4 text-ink-green-6"
                aria-hidden="true"
              />
            </div>
            <span class="mt-1.5 text-p-sm font-medium text-ink-gray-7">{{ p.label }}</span>
          </button>
        </div>
      </section>

      <!-- Accesos rápidos -->
      <section class="mb-8">
        <h2 class="mb-3 text-lg font-semibold text-ink-gray-9">Accesos rápidos</h2>
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <button
            v-for="a in accesos"
            :key="a.label"
            class="group flex flex-col items-center gap-2 rounded-lg border border-outline-gray-1 bg-surface-base p-4 text-center transition-[transform,box-shadow,border-color] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] hover:-translate-y-0.5 hover:border-upeu-navy/25 hover:shadow-md active:scale-[0.98]"
            @click="abrirAcceso(a)"
          >
            <span
              class="flex size-10 items-center justify-center rounded-full bg-upeu-navy-050 text-upeu-navy transition-colors group-hover:bg-upeu-navy group-hover:text-white"
            >
              <span :class="a.icon" class="size-5" aria-hidden="true" />
            </span>
            <span class="text-p-sm font-medium text-ink-gray-8">{{ a.label }}</span>
          </button>
        </div>
      </section>

      <p class="text-p-xs text-ink-gray-5">
        El menú de la izquierda te lleva a cada área del sistema; las migas de pan (arriba) indican dónde estás.
      </p>
    </div>
  </ScrollArea>
</template>
