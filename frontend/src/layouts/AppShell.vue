<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  Avatar,
  Breadcrumbs,
  DesktopShell,
  Dropdown,
  PageHeader,
  ScrollArea,
  Sidebar,
  SidebarItem,
  SidebarLabel,
  useTheme,
} from 'frappe-ui'
import { AREAS } from '@/data/areas'
import { useSessionStore } from '@/stores/session'
import upeuLogo from '@/assets/upeu-logo.png'

const route = useRoute()
const session = useSessionStore()
const { currentTheme, toggleTheme, setTheme } = useTheme()

// El producto inicia en claro; cada persona puede seleccionar oscuro y su
// preferencia queda persistida por frappe-ui en localStorage.
onMounted(() => {
  if (!localStorage.getItem('theme')) setTheme('light')
})

const themeActionLabel = computed(() =>
  currentTheme.value === 'dark' ? 'Activar modo claro' : 'Activar modo oscuro',
)

function areaFor(doctype) {
  const area = AREAS.find((a) => a.items.some((i) => i.doctype === doctype))
  const item = area?.items.find((i) => i.doctype === doctype)
  return { area, item }
}

const breadcrumbs = computed(() => {
  const items = [{ label: 'SGC UPeU', route: { name: 'Home' } }]
  if (route.name === 'DoctypeList' || route.name === 'DocNew') {
    const { area, item } = areaFor(route.params.doctype)
    if (area) items.push({ label: area.label })
    if (item) items.push({ label: item.label, route: { name: 'DoctypeList', params: { doctype: route.params.doctype } } })
    if (route.name === 'DocNew') items.push({ label: 'Nuevo' })
  } else if (route.name === 'DocForm') {
    const { area, item } = areaFor(route.params.doctype)
    if (area) items.push({ label: area.label })
    if (item) items.push({ label: item.label, route: { name: 'DoctypeList', params: { doctype: route.params.doctype } } })
    items.push({ label: route.params.name })
  } else if (route.name === 'Tablero') {
    items.push({ label: 'Tablero de indicadores' })
  } else if (route.name === 'TableroEjecutivo') {
    items.push({ label: 'Tablero ejecutivo' })
  } else if (route.name === 'AutoevaluacionDetalle') {
    items.push({ label: 'Acreditación' })
    items.push({ label: 'Autoevaluación', route: { name: 'DoctypeList', params: { doctype: 'Autoevaluacion' } } })
    items.push({ label: route.params.name })
  }
  return items
})

const userMenu = [
  {
    label: 'Cerrar sesión',
    icon: 'lucide-log-out',
    onClick: () => session.logout(),
  },
]

const initials = computed(() =>
  session.displayName
    .split(/[\s.@]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase(),
)

</script>

<template>
  <div class="sgc-shell h-screen w-full bg-surface-base text-ink-gray-9">
    <DesktopShell>
      <template #sidebar>
        <Sidebar
          width="14rem"
          data-theme="dark"
          class="sgc-app-sidebar border-r border-black/20 bg-gradient-to-b from-[#023052] via-upeu-navy to-[#00477e]"
        >
          <!-- Marca institucional = acceso a Inicio. El logo UPeU es azul marino,
               así que va sobre una tarjeta blanca (contraste). Toda la cabecera
               es un enlace a Inicio con feedback de press. -->
          <router-link
            :to="{ name: 'Home' }"
            class="brand-header group block shrink-0 px-2.5 pb-2 pt-3"
          >
            <div
              class="brand-card flex items-center justify-center rounded-xl bg-white px-3 py-2 shadow-sm ring-1 ring-black/5 transition-[transform,box-shadow] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] group-hover:shadow-md group-active:scale-[0.98]"
            >
              <img :src="upeuLogo" alt="Universidad Peruana Unión" class="h-8 w-full object-contain" />
            </div>
            <div class="mt-2.5 px-0.5">
              <div class="flex items-center gap-1.5">
                <span class="h-3 w-1 rounded-full bg-upeu-gold" aria-hidden="true" />
                <span class="text-[10px] font-semibold uppercase tracking-[0.15em] text-white/70">
                  Sistema de Gestión de la Calidad
                </span>
              </div>
            </div>
          </router-link>

          <ScrollArea class="min-h-0 flex-1" viewport-class="px-2.5 pt-1 pb-10">
            <nav class="space-y-0.5">
              <SidebarItem :to="{ name: 'Home' }">
                <template #prefix>
                  <span class="lucide-layout-dashboard size-4" aria-hidden="true" />
                </template>
                <span class="flex-1 truncate text-sm">Inicio</span>
              </SidebarItem>
              <SidebarItem :to="{ name: 'TableroEjecutivo' }">
                <template #prefix>
                  <span class="lucide-gauge size-4" aria-hidden="true" />
                </template>
                <span class="flex-1 truncate text-sm">Tablero ejecutivo</span>
              </SidebarItem>
              <SidebarItem :to="{ name: 'Tablero' }">
                <template #prefix>
                  <span class="lucide-bar-chart-3 size-4" aria-hidden="true" />
                </template>
                <span class="flex-1 truncate text-sm">Tablero de indicadores</span>
              </SidebarItem>
            </nav>

            <div v-for="area in AREAS" :key="area.label" class="mt-5">
              <div class="flex h-7 items-center">
                <SidebarLabel>{{ area.label }}</SidebarLabel>
              </div>
              <nav class="mt-0.5 space-y-0.5">
                <SidebarItem
                  v-for="item in area.items"
                  :key="item.doctype"
                  :to="{ name: 'DoctypeList', params: { doctype: item.doctype } }"
                >
                  <template #prefix>
                    <span :class="area.icon" class="size-4" aria-hidden="true" />
                  </template>
                  <span class="flex-1 truncate text-sm">{{ item.label }}</span>
                </SidebarItem>
              </nav>
            </div>
          </ScrollArea>

          <div class="mt-auto flex items-center gap-2 border-t border-white/10 p-2">
            <Dropdown :options="userMenu">
              <template #default="{ open }">
                <button
                  class="flex w-full items-center gap-2 rounded p-1.5 text-left hover:bg-white/10"
                  :class="{ 'bg-white/10': open }"
                >
                  <Avatar :label="session.displayName" size="sm">{{ initials }}</Avatar>
                  <span class="flex-1 truncate text-sm text-ink-gray-8">{{ session.displayName }}</span>
                </button>
              </template>
            </Dropdown>
          </div>
        </Sidebar>
      </template>

      <PageHeader class="sgc-app-header">
        <Breadcrumbs :items="breadcrumbs" />
        <div class="flex items-center gap-3">
          <div
            class="hidden items-center gap-2 rounded-md border border-outline-gray-2 bg-surface-gray-1 px-3 py-1.5 text-sm text-ink-gray-5 sm:flex"
            title="Búsqueda global — próximamente"
          >
            <span class="lucide-search size-3.5" aria-hidden="true" />
            <span>Buscar en el sistema…</span>
          </div>
          <button
            type="button"
            class="sgc-theme-toggle flex size-9 items-center justify-center rounded-md border border-outline-gray-2 bg-surface-white text-ink-gray-6"
            :aria-label="themeActionLabel"
            :title="themeActionLabel"
            @click="toggleTheme"
          >
            <span
              :class="currentTheme === 'dark' ? 'lucide-sun' : 'lucide-moon'"
              class="size-4"
              aria-hidden="true"
            />
          </button>
          <Dropdown :options="userMenu">
            <template #default>
              <button class="rounded-full transition-opacity duration-150 hover:opacity-80">
                <Avatar :label="session.displayName" size="lg">{{ initials }}</Avatar>
              </button>
            </template>
          </Dropdown>
        </div>
      </PageHeader>

      <router-view />
    </DesktopShell>
  </div>
</template>

<style scoped>
.sgc-app-sidebar :deep([data-slot='sidebar-item']) {
  height: 2rem;
  border-radius: 8px;
  color: rgb(255 255 255 / 0.72) !important;
}

.sgc-app-sidebar :deep([data-slot='sidebar-item'][data-state='active']) {
  background: rgb(255 255 255 / 0.14) !important;
  box-shadow: inset 2px 0 0 #f7a800;
  color: #ffffff !important;
}

.sgc-app-sidebar :deep([data-slot='sidebar-item'] a) {
  color: inherit !important;
}

.sgc-app-sidebar :deep([data-slot='sidebar-label'] h3) {
  color: rgb(255 255 255 / 0.5) !important;
  font-size: 0.68rem;
  font-weight: 650;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

/* La marca es un enlace ocasional (navegación), así que un feedback sutil de
   press es apropiado; se anula bajo prefers-reduced-motion. */
@media (prefers-reduced-motion: reduce) {
  .brand-card {
    transition: box-shadow 200ms ease;
  }
  .brand-header:active .brand-card {
    transform: none;
  }
}
</style>
