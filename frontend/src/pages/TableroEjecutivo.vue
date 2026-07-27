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

// GRC — riesgos (ISO 9001 §6.1), auditoría (§9.2) y revisión por la dirección (§9.3).
const NIVELES_RIESGO_VACIO = { Bajo: 0, Moderado: 0, Alto: 0, Extremo: 0, sin_evaluar: 0 }
const riesgos = computed(() => panel.data?.riesgos || {
  total: 0, abiertos: 0, criticos: 0, materializados: 0, cerrados: 0,
  por_estado: {}, por_nivel: { ...NIVELES_RIESGO_VACIO },
})
const auditoria = computed(() => panel.data?.auditoria || {
  total: 0, por_estado: {}, hallazgos: { total: 0, abiertos: 0, por_tipo: {}, por_estado: {} },
})
const revision = computed(() => panel.data?.revision_direccion || { total: 0, por_estado: {}, ultima: null })

// Niveles de riesgo, de mayor a menor severidad (el nivel sale de Evaluacion
// Riesgo: residual y, si no hay, inherente; `sin_evaluar` es dato faltante).
const NIVELES_RIESGO = [
  { clave: 'Extremo', chip: 'bg-surface-red-2 text-ink-red-6' },
  { clave: 'Alto', chip: 'bg-surface-red-1 text-ink-red-5' },
  { clave: 'Moderado', chip: 'bg-surface-amber-2 text-ink-amber-7' },
  { clave: 'Bajo', chip: 'bg-surface-green-2 text-ink-green-6' },
  { clave: 'sin_evaluar', chip: 'bg-surface-gray-2 text-ink-gray-6' },
]

const ESTADOS_AUDITORIA = ['Planificada', 'En ejecucion', 'Ejecutada', 'Informe emitido', 'Cerrada']

// Solo los tipos de hallazgo con conteo > 0 (la lista completa son 6 y satura).
const tiposHallazgo = computed(() =>
  Object.entries(auditoria.value.hallazgos?.por_tipo || {}).filter(([, n]) => n > 0),
)

function irA(doctype) {
  router.push({ name: 'DoctypeList', params: { doctype } })
}

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
      <section class="sb-hero mb-8 px-6 py-7 text-white sm:px-8">
        <div class="relative z-10 flex flex-wrap items-end justify-between gap-5">
          <div class="flex items-start gap-4">
            <span class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-white/10 text-marca-secundaria-300">
              <span class="lucide-gauge size-5" aria-hidden="true" />
            </span>
            <div>
              <p class="text-xs font-bold uppercase tracking-[0.14em] text-white/65">Acreditación institucional</p>
              <h1 class="mt-1 font-display text-3xl font-bold tracking-tight">Tablero ejecutivo</h1>
              <p class="mt-2 text-p-sm text-white/75">Cobertura, niveles y alertas de los programas de la UPeU.</p>
            </div>
          </div>
          <div class="rounded-xl border border-white/15 bg-white/[0.07] px-4 py-3">
            <div class="text-2xl font-bold tabular-nums text-marca-secundaria-300">{{ cobertura.pct }}%</div>
            <div class="text-xs font-semibold uppercase tracking-[0.08em] text-white/65">Cobertura actual</div>
          </div>
        </div>
      </section>

      <div v-if="panel.loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="h-28 animate-pulse rounded-xl border border-outline-gray-1 bg-surface-gray-1" />
      </div>

      <template v-else>
        <!-- Cobertura + mejora -->
        <section class="mb-6 grid gap-3 sm:grid-cols-3">
          <div class="sb-card bg-gradient-to-b from-marca-primaria-50 to-surface-base p-5 sm:col-span-2">
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
            <div class="sb-card p-4" :class="mejora.nc_abiertas ? 'border-outline-red-1 bg-surface-red-1' : ''">
              <div class="font-display text-2xl font-bold" :class="mejora.nc_abiertas ? 'text-ink-red-5' : 'text-ink-gray-4'">
                {{ mejora.nc_abiertas }}
              </div>
              <div class="text-p-xs text-ink-gray-6">No conformidades abiertas</div>
            </div>
            <div class="sb-card p-4" :class="mejora.planes_riesgo ? 'border-outline-red-1 bg-surface-red-1' : ''">
              <div class="font-display text-2xl font-bold" :class="mejora.planes_riesgo ? 'text-ink-red-5' : 'text-ink-gray-4'">
                {{ mejora.planes_riesgo }}
              </div>
              <div class="text-p-xs text-ink-gray-6">Planes de mejora en riesgo</div>
            </div>
          </div>
        </section>

        <!-- Distribución de niveles -->
        <section class="sb-card mb-6 p-5">
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
        <section v-if="cbc" class="sb-card mb-6 p-5">
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

        <!-- Riesgos (ISO 9001 §6.1) -->
        <section class="sb-card mb-6 p-5">
          <div class="mb-3 flex flex-wrap items-center gap-2">
            <h2 class="text-lg font-semibold text-ink-gray-9">Riesgos abiertos</h2>
            <button class="sb-interactive ml-auto text-p-xs font-semibold text-marca-primaria-700" @click="irA('Riesgo')">
              Ver inventario
            </button>
          </div>
          <div v-if="!riesgos.total" class="text-p-sm text-ink-gray-5">
            Aún no hay riesgos registrados.
          </div>
          <template v-else>
            <div class="grid gap-3 sm:grid-cols-3">
              <div class="rounded-lg bg-surface-gray-1 p-3">
                <div class="font-display text-2xl font-bold text-ink-gray-8">{{ riesgos.abiertos }}</div>
                <div class="text-p-xs text-ink-gray-6">Abiertos (de {{ riesgos.total }})</div>
              </div>
              <div class="rounded-lg p-3" :class="riesgos.criticos ? 'bg-surface-red-1' : 'bg-surface-gray-1'">
                <div class="font-display text-2xl font-bold" :class="riesgos.criticos ? 'text-ink-red-5' : 'text-ink-gray-4'">
                  {{ riesgos.criticos }}
                </div>
                <div class="text-p-xs text-ink-gray-6">Nivel Alto o Extremo</div>
              </div>
              <div class="rounded-lg p-3" :class="riesgos.materializados ? 'bg-surface-red-1' : 'bg-surface-gray-1'">
                <div class="font-display text-2xl font-bold" :class="riesgos.materializados ? 'text-ink-red-5' : 'text-ink-gray-4'">
                  {{ riesgos.materializados }}
                </div>
                <div class="text-p-xs text-ink-gray-6">Materializados</div>
              </div>
            </div>
            <div class="mt-3 flex flex-wrap gap-2">
              <span
                v-for="n in NIVELES_RIESGO"
                :key="n.clave"
                class="rounded-full px-2.5 py-0.5 text-xs font-semibold"
                :class="n.chip"
              >
                {{ n.clave === 'sin_evaluar' ? 'Sin evaluar' : n.clave }}: {{ riesgos.por_nivel?.[n.clave] || 0 }}
              </span>
            </div>
            <p v-if="riesgos.por_nivel?.sin_evaluar" class="mt-2 text-p-xs text-ink-gray-5">
              «Sin evaluar» son riesgos abiertos sin evaluación de nivel registrada: el nivel no se estima.
            </p>
          </template>
        </section>

        <!-- Auditoría interna (ISO 9001 §9.2) -->
        <section class="sb-card mb-6 p-5">
          <div class="mb-3 flex flex-wrap items-center gap-2">
            <h2 class="text-lg font-semibold text-ink-gray-9">Auditoría interna</h2>
            <button class="sb-interactive ml-auto text-p-xs font-semibold text-marca-primaria-700" @click="irA('Hallazgo Auditoria')">
              Ver hallazgos
            </button>
          </div>
          <div v-if="!auditoria.total" class="text-p-sm text-ink-gray-5">
            Aún no hay auditorías registradas.
          </div>
          <template v-else>
            <div class="grid gap-3 sm:grid-cols-3">
              <div class="rounded-lg bg-surface-gray-1 p-3">
                <div class="font-display text-2xl font-bold text-ink-gray-8">{{ auditoria.total }}</div>
                <div class="text-p-xs text-ink-gray-6">Auditorías</div>
              </div>
              <div class="rounded-lg bg-surface-gray-1 p-3">
                <div class="font-display text-2xl font-bold text-ink-gray-8">{{ auditoria.hallazgos?.total || 0 }}</div>
                <div class="text-p-xs text-ink-gray-6">Hallazgos</div>
              </div>
              <div class="rounded-lg p-3" :class="auditoria.hallazgos?.abiertos ? 'bg-surface-amber-1' : 'bg-surface-gray-1'">
                <div class="font-display text-2xl font-bold" :class="auditoria.hallazgos?.abiertos ? 'text-ink-amber-7' : 'text-ink-gray-4'">
                  {{ auditoria.hallazgos?.abiertos || 0 }}
                </div>
                <div class="text-p-xs text-ink-gray-6">Hallazgos abiertos</div>
              </div>
            </div>
            <div class="mt-3 flex flex-wrap gap-2">
              <span
                v-for="e in ESTADOS_AUDITORIA"
                :key="e"
                v-show="auditoria.por_estado?.[e]"
                class="rounded-full bg-surface-gray-2 px-2.5 py-0.5 text-xs font-semibold text-ink-gray-7"
              >
                {{ e }}: {{ auditoria.por_estado[e] }}
              </span>
            </div>
            <div v-if="tiposHallazgo.length" class="mt-2 flex flex-wrap gap-2">
              <span
                v-for="[tipo, n] in tiposHallazgo"
                :key="tipo"
                class="rounded-full bg-surface-amber-1 px-2.5 py-0.5 text-xs font-semibold text-ink-amber-7"
              >
                {{ tipo }}: {{ n }}
              </span>
            </div>
          </template>
        </section>

        <!-- Revisión por la dirección (ISO 9001 §9.3) -->
        <section class="sb-card mb-6 p-5">
          <div class="mb-3 flex flex-wrap items-center gap-2">
            <h2 class="text-lg font-semibold text-ink-gray-9">Revisión por la dirección</h2>
            <button class="sb-interactive ml-auto text-p-xs font-semibold text-marca-primaria-700" @click="irA('Revision Direccion')">
              Ver revisiones
            </button>
          </div>
          <div v-if="!revision.ultima" class="text-p-sm text-ink-gray-5">
            Aún no se ha registrado ninguna revisión por la dirección (§9.3).
          </div>
          <template v-else>
            <div class="flex flex-wrap items-baseline gap-2">
              <span class="font-semibold text-ink-gray-9">{{ revision.ultima.titulo || revision.ultima.codigo }}</span>
              <span class="rounded-full bg-surface-gray-2 px-2.5 py-0.5 text-xs font-semibold text-ink-gray-7">
                {{ revision.ultima.estado }}
              </span>
              <span class="text-p-xs text-ink-gray-5">{{ revision.ultima.fecha || 'sin fecha' }}</span>
            </div>
            <div class="mt-2 text-p-xs text-ink-gray-5">
              Última de {{ revision.total }} revisión(es) registrada(s).
            </div>
          </template>
        </section>

        <!-- Por programa -->
        <section>
          <h2 class="mb-3 text-lg font-semibold text-ink-gray-9">Por programa</h2>
          <div v-if="!programas.length" class="sb-empty-state text-p-sm">
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
