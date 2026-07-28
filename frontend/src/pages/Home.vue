<script setup>
import { computed, ref } from 'vue'
import { useCall } from 'frappe-ui'
import { useRouter } from 'vue-router'
import AreaScroll from '@/components/ui/AreaScroll.vue'
import { AngleDown, Check, ClipboardCheck, Compass, Flag, Link2, Paperclip, ShieldCheck } from 'reicon-vue'
import { GUIAS_ROL } from '@/data/guias-rol'

const router = useRouter()

// Guía rápida por rol (mini-manual en contexto). Permanece disponible sin
// desplazar los datos operativos que la persona consulta a diario.
const guiaAbierta = ref(false)
const guiaSel = ref(0)
const guia = computed(() => GUIAS_ROL[guiaSel.value])
const MANUAL_URL = 'https://sciback.github.io/sgc/manual-uso/primeros-pasos/'

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
  if (!p.valor) return { card: 'border-borde', num: 'text-tinta-tenue', chip: 'bg-superficie-3 text-tinta-tenue', al_dia: true }
  if (p.tono === 'rojo') return { card: 'border-peligro-tenue bg-peligro-tenue', num: 'text-peligro', chip: 'bg-peligro-tenue text-peligro' }
  return { card: 'border-aviso-tenue bg-aviso-tenue', num: 'text-aviso', chip: 'bg-aviso-tenue text-aviso' }
}

function irA(doctype) {
  router.push({ name: 'DoctypeList', params: { doctype } })
}

// Los iconos son COMPONENTES, no cadenas (estilo SciBack §3). Pack de la casa: reicon.
const accesos = [
  { label: 'Autoevaluación', icon: ClipboardCheck, doctype: 'Autoevaluacion' },
  { label: 'Cargar evidencia', icon: Paperclip, doctype: 'Evidencia', nuevo: true },
  { label: 'Diagnóstico CBC', icon: ShieldCheck, doctype: 'Informe Cumplimiento' },
  { label: 'Registrar hallazgo', icon: Flag, doctype: 'Hallazgo', nuevo: true },
]

function abrirAcceso(a) {
  router.push({ name: 'DoctypeList', params: { doctype: a.doctype } })
}
</script>

<template>
  <AreaScroll class="min-h-0 flex-1">
    <div class="sgc-home mx-auto max-w-7xl px-6 py-8 sm:px-8 xl:px-10">
      <!-- Hero SciBack: cromo institucional; los indicadores siguen siendo los
           mismos datos operativos de Inicio, no un módulo adicional. -->
      <section class="sb-hero mb-8 px-6 py-7 text-white sm:px-8">
        <div class="relative z-10 flex flex-wrap items-end justify-between gap-6">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.14em] text-white/70">
              Universidad Peruana Unión · Dirección de Gestión de la Calidad
            </p>
            <h1 class="mt-2 font-display text-3xl font-bold tracking-[-0.035em] sm:text-4xl">Panel de calidad</h1>
            <p class="mt-2 max-w-xl text-sm leading-6 text-white/75">
              Panorama operativo de acreditación, evidencias y mejora continua.
            </p>
          </div>
          <div class="flex gap-6 text-sm">
            <div>
              <div class="text-2xl font-bold tabular-nums text-marca-secundaria-300">{{ programasTotal }}</div>
              <div class="mt-0.5 text-xs font-semibold uppercase tracking-[0.08em] text-white/60">Programas</div>
            </div>
            <div>
              <div class="text-2xl font-bold tabular-nums text-white">{{ totalAtencion }}</div>
              <div class="mt-0.5 text-xs font-semibold uppercase tracking-[0.08em] text-white/60">Pendientes</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Guía rápida por rol (mini-manual en contexto) -->
      <section class="sb-card mb-8 overflow-hidden">
        <button
          class="btn-press flex w-full items-center gap-3 px-5 py-4 text-left transition-[background-color] duration-150 hover:bg-superficie-2"
          @click="guiaAbierta = !guiaAbierta"
        >
          <span class="flex size-9 shrink-0 items-center justify-center rounded-xl bg-marca-primaria-50 text-marca-primaria-700">
            <Compass :size="16" aria-hidden="true" />
          </span>
          <span class="flex-1">
            <span class="block text-sm font-semibold text-tinta">¿No sabes por dónde empezar?</span>
            <span class="block text-xs text-tinta-tenue">Guía rápida según tu rol — qué hacer, paso a paso.</span>
          </span>
          <AngleDown
            :size="20"
            class="text-tinta-tenue transition-transform duration-200 ease-[cubic-bezier(0.23,1,0.32,1)]"
            :class="guiaAbierta && 'rotate-180'"
            aria-hidden="true"
          />
        </button>

        <div v-if="guiaAbierta" class="border-t border-borde px-5 py-5">
          <div class="mb-4 flex flex-wrap gap-2">
            <button
              v-for="(g, i) in GUIAS_ROL"
              :key="g.rol"
              class="rounded-full border px-3 py-1 text-sm font-medium transition-colors duration-150"
              :class="i === guiaSel ? 'border-marca-primaria-700 bg-marca-primaria-700 text-white' : 'border-borde-fuerte text-tinta-suave hover:border-marca-primaria-300'"
              @click="guiaSel = i"
            >
              {{ g.corto }}
            </button>
          </div>

          <p class="mb-3 text-sm text-tinta-suave">
            <b class="text-tinta">{{ guia.rol }}.</b> {{ guia.resumen }}
          </p>
          <ol class="space-y-2">
            <li v-for="(paso, i) in guia.pasos" :key="i" class="flex gap-2.5 text-sm text-tinta-suave">
              <span class="flex size-5 shrink-0 items-center justify-center rounded-full bg-marca-primaria-50 text-xs font-bold text-marca-primaria-700">
                {{ i + 1 }}
              </span>
              <span>{{ paso }}</span>
            </li>
          </ol>
          <p class="mt-3 rounded-lg bg-superficie-2 px-3 py-2 text-xs text-tinta-suave">
            <Flag :size="14" class="mr-1 inline align-text-bottom" aria-hidden="true" />{{ guia.fin }}
          </p>
          <a
            :href="MANUAL_URL"
            target="_blank"
            rel="noopener"
            class="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-marca-primaria-700 hover:opacity-70"
          >
            Ver la guía completa
            <Link2 :size="14" aria-hidden="true" />
          </a>
        </div>
      </section>

      <!-- Autoevaluaciones (multi-programa: 1..22 de la UPeU) -->
      <section class="mb-8">
        <div class="mb-3 flex flex-wrap items-center gap-2">
          <h2 class="text-lg font-semibold text-tinta">Autoevaluaciones</h2>
          <span
            v-if="!panel.loading && programasTotal"
            class="rounded-full bg-marca-primaria-50 px-2.5 py-0.5 text-xs font-semibold text-marca-primaria-700"
          >
            {{ autoevals.length }} de {{ programasTotal }} programas iniciados
          </span>
          <button
            class="ml-auto text-sm font-semibold text-marca-primaria-700 transition-opacity hover:opacity-70"
            @click="irA('Autoevaluacion')"
          >
            Ver todas →
          </button>
        </div>

        <div v-if="panel.loading" class="space-y-3">
          <div v-for="i in 2" :key="i" class="h-28 animate-pulse rounded-xl border border-borde bg-superficie-2" />
        </div>

        <div
          v-else-if="!autoevals.length"
          class="rounded-xl border border-dashed border-borde-fuerte bg-superficie-2 p-6 text-center"
        >
          <p class="text-sm font-medium text-tinta-suave">Aún no hay autoevaluaciones iniciadas.</p>
          <p class="mt-1 text-sm text-tinta-tenue">
            Los {{ programasTotal }} programas de la UPeU están configurados; crea la primera desde Autoevaluación.
          </p>
        </div>

        <div
          v-else
          class="grid gap-4"
          :class="autoevals.length === 1 ? 'max-w-4xl grid-cols-1' : 'md:grid-cols-2 2xl:grid-cols-3'"
        >
          <button
            v-for="ae in autoevals"
            :key="ae.name"
            class="sb-card sb-interactive group flex min-h-[172px] flex-col p-6 text-left"
            @click="abrirAutoeval(ae)"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <h3 class="truncate text-lg font-semibold tracking-[-0.02em] text-tinta">
                  {{ ae.programa_sede || ae.titulo || ae.name }}
                </h3>
                <div class="mt-0.5 truncate text-xs text-tinta-tenue">
                  {{ ae.periodo_academico }} · {{ ae.marco_normativo }}
                </div>
              </div>
              <span class="shrink-0 rounded-full bg-superficie-3 px-2 py-0.5 text-xs font-medium text-tinta-suave">
                {{ ae.estado }}
              </span>
            </div>

            <div class="mt-4">
              <div class="mb-1 flex items-baseline justify-between">
                <span class="text-xs font-medium text-tinta-suave">Avance</span>
                <span class="text-base font-semibold tabular-nums text-marca-primaria-700">{{ avanceDe(ae) }}%</span>
              </div>
              <div class="h-2 w-full overflow-hidden rounded-full bg-superficie-3">
                <div
                  class="h-full rounded-full bg-marca-primaria-700 transition-[width] duration-500 ease-[cubic-bezier(0.23,1,0.32,1)]"
                  :style="{ width: avanceDe(ae) + '%' }"
                />
              </div>
              <div class="mt-1.5 text-xs text-tinta-tenue">
                {{ ae.criterios_valorados }} de {{ ae.criterios_total }} criterios
                <template v-if="ae.criterios_pendientes">
                  · <b class="text-aviso">{{ ae.criterios_pendientes }} sin valorar</b>
                </template>
              </div>
            </div>
          </button>
        </div>
      </section>

      <!-- Requiere atención -->
      <section class="mb-8">
        <div class="mb-3 flex items-center gap-2">
          <h2 class="text-lg font-semibold text-tinta">Requiere atención</h2>
          <span
            v-if="!panel.loading"
            class="rounded-full px-2 py-0.5 text-xs font-semibold"
            :class="totalAtencion ? 'bg-aviso-tenue text-aviso' : 'bg-exito-tenue text-exito'"
          >
            {{ totalAtencion ? `${totalAtencion} pendientes` : 'Todo al día' }}
          </span>
        </div>

        <div v-if="panel.loading" class="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div v-for="i in 6" :key="i" class="h-24 animate-pulse rounded-lg border border-borde bg-superficie-2" />
        </div>

        <div v-else class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <button
            v-for="p in pendientes"
            :key="p.clave"
            class="sb-interactive group flex min-h-[112px] flex-col items-start rounded-xl border p-4 text-left"
            :class="tono(p).card"
            @click="irA(p.doctype)"
          >
            <div class="flex w-full items-center justify-between">
              <span class="text-3xl font-semibold tabular-nums" :class="tono(p).num">{{ p.valor }}</span>
              <Check
                v-if="tono(p).al_dia"
                :size="16"
                class="text-exito"
                aria-hidden="true"
              />
            </div>
            <span class="mt-1.5 text-sm font-medium text-tinta-suave">{{ p.label }}</span>
          </button>
        </div>
      </section>

      <!-- Accesos rápidos -->
      <section class="mb-8">
        <h2 class="mb-3 text-lg font-semibold text-tinta">Accesos rápidos</h2>
        <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
          <button
            v-for="a in accesos"
            :key="a.label"
            class="sb-card sb-interactive group flex min-h-[132px] flex-col items-center justify-center gap-2 p-4 text-center"
            @click="abrirAcceso(a)"
          >
            <span
              class="flex size-10 items-center justify-center rounded-xl bg-marca-primaria-50 text-marca-primaria-700 transition-[background-color,color] duration-150 group-hover:bg-marca-primaria-700 group-hover:text-white"
            >
              <component :is="a.icon" :size="20" aria-hidden="true" />
            </span>
            <span class="text-sm font-medium text-tinta">{{ a.label }}</span>
          </button>
        </div>
      </section>

      <p class="text-xs text-tinta-tenue">
        El menú de la izquierda te lleva a cada área del sistema; las migas de pan (arriba) indican dónde estás.
      </p>
    </div>
  </AreaScroll>
</template>
