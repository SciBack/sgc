<script setup>
import { computed } from 'vue'
import { ScrollArea, useCall } from 'frappe-ui'
import { useRouter } from 'vue-router'

const router = useRouter()

// M13 — vista institucional: cómo va la acreditación en TODOS los programas.
const panel = useCall({
  url: '/api/v2/method/sgc.tablero_ejecutivo.resumen_ejecutivo',
  cacheKey: 'tablero-ejecutivo',
})

const cobertura = computed(() => panel.data?.cobertura || { programas_total: 0, con_autoevaluacion: 0, pct: 0 })
const programas = computed(() => panel.data?.programas || [])
const niveles = computed(() => panel.data?.niveles || { NL: 0, L: 0, LP: 0, sin_valorar: 0 })
const cbc = computed(() => panel.data?.cbc || null)
const mejora = computed(() => panel.data?.mejora || { nc_abiertas: 0, planes_riesgo: 0 })

const totalEstandares = computed(() =>
  Object.values(niveles.value).reduce((n, v) => n + (v || 0), 0),
)

// Segmentos de la barra apilada de niveles (orden: logro alto -> sin valorar).
const SEGMENTOS = [
  { clave: 'LP', label: 'Logrado plenamente', bg: 'bg-surface-green-6', chip: 'bg-surface-green-2 text-ink-green-6' },
  { clave: 'L', label: 'Logrado', bg: 'bg-surface-amber-5', chip: 'bg-surface-amber-2 text-ink-amber-7' },
  { clave: 'NL', label: 'No logrado', bg: 'bg-surface-red-5', chip: 'bg-surface-red-2 text-ink-red-6' },
  { clave: 'sin_valorar', label: 'Sin valorar', bg: 'bg-surface-gray-4', chip: 'bg-surface-gray-2 text-ink-gray-6' },
]

function pctDe(clave) {
  const t = totalEstandares.value
  return t ? (niveles.value[clave] || 0) * 100 / t : 0
}

const semaforoCbc = {
  Verde: 'bg-surface-green-2 text-ink-green-6',
  Ambar: 'bg-surface-amber-2 text-ink-amber-7',
  Rojo: 'bg-surface-red-2 text-ink-red-6',
}

function abrirAutoeval(p) {
  router.push({ name: 'AutoevaluacionDetalle', params: { name: p.name } })
}
</script>

<template>
  <ScrollArea class="min-h-0 flex-1">
    <div class="mx-auto max-w-7xl px-6 py-8 sm:px-8 xl:px-10">
      <div class="mb-5">
        <div class="text-xs font-semibold uppercase tracking-wide text-marca-primaria-700 opacity-75">
          Acreditación institucional
        </div>
        <h1 class="mt-1 font-display text-3xl font-bold tracking-tight text-marca-primaria-700">Tablero ejecutivo</h1>
      </div>

      <div v-if="panel.loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-28 animate-pulse rounded-xl border border-outline-gray-1 bg-surface-gray-1" />
      </div>

      <template v-else>
        <!-- Cobertura + mejora -->
        <section class="mb-6 grid gap-3 sm:grid-cols-3">
          <div class="rounded-xl border border-outline-gray-1 bg-gradient-to-b from-marca-primaria-50 to-surface-base p-5 sm:col-span-2">
            <div class="text-xs font-semibold uppercase tracking-wide text-marca-primaria-700 opacity-75">
              Cobertura de autoevaluación
            </div>
            <div class="mt-1 flex items-baseline gap-2">
              <span class="font-display text-3xl font-bold text-marca-primaria-700">
                {{ cobertura.con_autoevaluacion }} <span class="text-ink-gray-5">/ {{ cobertura.programas_total }}</span>
              </span>
              <span class="text-p-sm text-ink-gray-6">programas con autoevaluación iniciada</span>
            </div>
            <div class="mt-3 h-2 w-full overflow-hidden rounded-full bg-surface-gray-3">
              <div
                class="h-full rounded-full bg-marca-primaria-700 transition-[width] duration-500 ease-[cubic-bezier(0.23,1,0.32,1)]"
                :style="{ width: cobertura.pct + '%' }"
              />
            </div>
            <div class="mt-1.5 text-p-xs text-ink-gray-5">{{ cobertura.pct }}% del total de programas</div>
          </div>

          <div class="grid gap-3">
            <div class="rounded-xl border p-4" :class="mejora.nc_abiertas ? 'border-outline-red-1 bg-surface-red-1' : 'border-outline-gray-1'">
              <div class="font-display text-2xl font-bold" :class="mejora.nc_abiertas ? 'text-ink-red-5' : 'text-ink-gray-4'">
                {{ mejora.nc_abiertas }}
              </div>
              <div class="text-p-xs text-ink-gray-6">No conformidades abiertas</div>
            </div>
            <div class="rounded-xl border p-4" :class="mejora.planes_riesgo ? 'border-outline-red-1 bg-surface-red-1' : 'border-outline-gray-1'">
              <div class="font-display text-2xl font-bold" :class="mejora.planes_riesgo ? 'text-ink-red-5' : 'text-ink-gray-4'">
                {{ mejora.planes_riesgo }}
              </div>
              <div class="text-p-xs text-ink-gray-6">Planes de mejora en riesgo</div>
            </div>
          </div>
        </section>

        <!-- Distribución de niveles -->
        <section class="mb-6 rounded-xl border border-outline-gray-1 bg-surface-base p-5">
          <h2 class="mb-3 text-lg font-semibold text-ink-gray-9">Estándares por nivel</h2>
          <div v-if="!totalEstandares" class="text-p-sm text-ink-gray-5">
            Aún no hay estándares valorados.
          </div>
          <template v-else>
            <div class="flex h-3 w-full overflow-hidden rounded-full bg-surface-gray-2">
              <div
                v-for="s in SEGMENTOS"
                :key="s.clave"
                class="h-full transition-[width] duration-500 ease-[cubic-bezier(0.23,1,0.32,1)]"
                :class="s.bg"
                :style="{ width: pctDe(s.clave) + '%' }"
                :title="`${s.label}: ${niveles[s.clave]}`"
              />
            </div>
            <div class="mt-3 flex flex-wrap gap-2">
              <span
                v-for="s in SEGMENTOS"
                :key="s.clave"
                class="rounded-full px-2.5 py-0.5 text-xs font-semibold"
                :class="s.chip"
              >
                {{ s.label }}: {{ niveles[s.clave] }}
              </span>
            </div>
            <div class="mt-2 text-p-xs text-ink-gray-5">{{ totalEstandares }} estándares en total</div>
          </template>
        </section>

        <!-- CBC -->
        <section v-if="cbc" class="mb-6 rounded-xl border border-outline-gray-1 bg-surface-base p-5">
          <div class="mb-3 flex flex-wrap items-center gap-2">
            <h2 class="text-lg font-semibold text-ink-gray-9">Condiciones Básicas de Calidad</h2>
            <span
              v-if="cbc.semaforo"
              class="rounded-full px-2.5 py-0.5 text-xs font-semibold"
              :class="semaforoCbc[cbc.semaforo] || 'bg-surface-gray-2 text-ink-gray-6'"
            >
              {{ cbc.semaforo }}
            </span>
            <span class="ml-auto text-p-xs text-ink-gray-5">{{ cbc.name }}</span>
          </div>
          <div class="grid grid-cols-3 gap-3">
            <div class="rounded-lg bg-surface-green-1 p-3">
              <div class="font-display text-2xl font-bold text-ink-green-6">{{ cbc.n_cumple ?? 0 }}</div>
              <div class="text-p-xs text-ink-gray-6">Cumple</div>
            </div>
            <div class="rounded-lg bg-surface-amber-1 p-3">
              <div class="font-display text-2xl font-bold text-ink-amber-7">{{ cbc.n_parcial ?? 0 }}</div>
              <div class="text-p-xs text-ink-gray-6">Cumple parcial</div>
            </div>
            <div class="rounded-lg bg-surface-red-1 p-3">
              <div class="font-display text-2xl font-bold text-ink-red-5">{{ cbc.n_no_cumple ?? 0 }}</div>
              <div class="text-p-xs text-ink-gray-6">No cumple</div>
            </div>
          </div>
        </section>

        <!-- Por programa -->
        <section>
          <h2 class="mb-3 text-lg font-semibold text-ink-gray-9">Por programa</h2>
          <div v-if="!programas.length" class="rounded-xl border border-dashed border-outline-gray-2 bg-surface-gray-1 p-6 text-center text-p-sm text-ink-gray-6">
            Aún no hay autoevaluaciones iniciadas.
          </div>
          <div v-else class="space-y-2">
            <button
              v-for="p in programas"
              :key="p.name"
              class="sb-interactive flex w-full flex-wrap items-center gap-3 rounded-xl border border-outline-gray-1 bg-surface-base p-4 text-left"
              @click="abrirAutoeval(p)"
            >
              <div class="min-w-[160px] flex-1">
                <div class="font-semibold text-ink-gray-9">{{ p.programa_sede || p.titulo || p.name }}</div>
                <div class="text-p-xs text-ink-gray-5">{{ p.periodo_academico }} · {{ p.estado }}</div>
              </div>
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="s in SEGMENTOS"
                  :key="s.clave"
                  v-show="p.niveles?.[s.clave]"
                  class="rounded px-1.5 py-0.5 text-xs font-semibold"
                  :class="s.chip"
                >
                  {{ s.clave === 'sin_valorar' ? '—' : s.clave }} {{ p.niveles[s.clave] }}
                </span>
              </div>
              <div class="w-28 shrink-0">
                <div class="mb-1 text-right text-p-xs font-semibold text-marca-primaria-700">{{ Math.round(p.avance_pct || 0) }}%</div>
                <div class="h-1.5 w-full overflow-hidden rounded-full bg-surface-gray-3">
                  <div class="h-full rounded-full bg-marca-primaria-700" :style="{ width: Math.round(p.avance_pct || 0) + '%' }" />
                </div>
              </div>
            </button>
          </div>
        </section>
      </template>
    </div>
  </ScrollArea>
</template>
