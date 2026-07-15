<script setup>
import { ScrollArea, useCall } from 'frappe-ui'
import { BLOCKS, STATUS_LABEL } from '@/data/modules'
import { useRouter } from 'vue-router'

const router = useRouter()

const statusTheme = {
  ok: { badge: 'text-ink-green-6 bg-surface-green-2', dot: 'bg-surface-green-7' },
  wip: { badge: 'text-ink-amber-6 bg-surface-amber-2', dot: 'bg-surface-amber-7' },
  pend: { badge: 'text-ink-gray-6 bg-surface-gray-2', dot: 'bg-surface-gray-5' },
}

// Conteos en vivo — misma idea que el bloque HTML del inicio interino
// (sgc_home_apply.py), pero pedidos vía la API en vez de embebidos.
const metrics = [
  { label: 'Marcos normativos cargados', doctype: 'Marco Normativo' },
  { label: 'Indicadores catalogados', doctype: 'Indicador' },
  { label: 'Programas con código INEI', doctype: 'Programa' },
  { label: 'Autoevaluaciones', doctype: 'Autoevaluacion' },
]

function countCall(doctype) {
  return useCall({
    // v2, no v1: v1 envuelve la respuesta en {"message": N}; useCall espera
    // el envelope v2 {"data": N}.
    url: '/api/v2/method/frappe.client.get_count',
    params: { doctype },
    cacheKey: ['count', doctype],
  })
}

const counts = metrics.map((m) => ({ ...m, resource: countCall(m.doctype) }))

function openModule(mod) {
  if (mod.doctype) {
    router.push({ name: 'DoctypeList', params: { doctype: mod.doctype } })
  }
}
</script>

<template>
  <ScrollArea class="min-h-0 flex-1">
    <div class="mx-auto max-w-5xl px-5 py-6 sm:px-8">
      <!-- Hero -->
      <section
        class="mb-6 flex flex-wrap items-stretch gap-6 rounded-xl border border-outline-gray-1 bg-gradient-to-b from-upeu-navy-050 to-surface-gray-1 p-7"
      >
        <div class="min-w-[280px] flex-1">
          <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-upeu-navy opacity-75">
            Universidad Peruana Unión · Dirección de Gestión de la Calidad
          </div>
          <h1 class="mb-3 font-display text-3xl font-bold tracking-tight text-upeu-navy">Índice del sistema</h1>
          <p class="mb-4 max-w-[64ch] text-p-base text-ink-gray-7">
            Mapa completo del Sistema de Gestión de la Calidad — los 18 módulos organizados en 4
            bloques, con su estado real. Todo lo que ya funciona y lo que falta, en un solo lugar.
          </p>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="chip in ['3 sedes', '22 programas', 'CONEAU · SUNEDU · ISO 21001']"
              :key="chip"
              class="rounded-full border border-outline-gray-2 bg-surface-base px-3 py-1 text-xs font-medium text-upeu-navy"
            >
              {{ chip }}
            </span>
          </div>
        </div>
        <div class="min-w-[220px] flex-none rounded-lg border border-outline-gray-1 bg-surface-base p-4">
          <div class="mb-3 text-xs font-semibold uppercase tracking-wide text-upeu-navy">Estado</div>
          <div v-for="(label, key) in STATUS_LABEL" :key="key" class="mb-2 flex items-center gap-2 text-sm text-ink-gray-6">
            <span class="size-2.5 shrink-0 rounded-full" :class="statusTheme[key].dot" />
            {{ label }}
          </div>
        </div>
      </section>

      <!-- Métricas -->
      <section class="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div
          v-for="m in counts"
          :key="m.doctype"
          class="rounded-lg border border-outline-gray-1 bg-surface-base p-4"
        >
          <div class="text-2xl font-bold text-upeu-navy">
            <span v-if="m.resource.loading">···</span>
            <span v-else>{{ m.resource.data ?? 0 }}</span>
          </div>
          <div class="mt-1 text-p-xs text-ink-gray-6">{{ m.label }}</div>
        </div>
      </section>

      <!-- Bloques de módulos -->
      <section v-for="block in BLOCKS" :key="block.letter" class="mb-8">
        <div class="mb-3 flex items-center gap-3 border-b border-outline-gray-1 pb-2.5">
          <div class="flex size-7 items-center justify-center rounded-md bg-upeu-navy font-display text-sm font-bold text-white">
            {{ block.letter }}
          </div>
          <div class="text-lg font-semibold text-ink-gray-9">{{ block.name }}</div>
          <div class="ml-auto text-xs text-ink-gray-5">{{ block.modules.length }} módulos</div>
        </div>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div
            v-for="mod in block.modules"
            :key="mod.code"
            class="flex cursor-pointer flex-col rounded-lg border border-outline-gray-1 bg-surface-base p-4 transition-[transform,box-shadow,border-color] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] hover:-translate-y-0.5 hover:border-upeu-navy/25 hover:shadow-md active:scale-[0.99]"
            @click="openModule(mod)"
          >
            <div class="mb-1 flex items-center gap-2">
              <span class="rounded bg-surface-gray-2 px-1.5 py-0.5 font-mono text-xs font-semibold text-ink-gray-6">
                {{ mod.code }}
              </span>
              <span
                class="ml-auto rounded-full px-2.5 py-0.5 text-xs font-semibold"
                :class="statusTheme[mod.status].badge"
              >
                {{ STATUS_LABEL[mod.status] }}
              </span>
            </div>
            <h3 class="mb-1.5 text-base font-semibold text-ink-gray-9">{{ mod.title }}</h3>
            <p class="mb-3 text-p-sm text-ink-gray-6">{{ mod.desc }}</p>
            <div class="mt-auto flex flex-wrap gap-1.5">
              <span
                v-for="tag in mod.tags"
                :key="tag"
                class="rounded border border-outline-gray-1 bg-surface-gray-1 px-2 py-0.5 text-xs text-ink-gray-7"
              >
                {{ tag }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <p class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 p-4 text-p-xs text-ink-gray-6">
        <b class="text-ink-gray-8">Este es el inicio del sistema.</b>
        El menú de la izquierda te lleva a cada área; las migas de pan (arriba) indican dónde estás.
      </p>
    </div>
  </ScrollArea>
</template>
