<script setup>
/**
 * Shell de la aplicación. Reconstruido con marcado propio y primitivas del
 * stack canónico: ya no usa `DesktopShell`, `Sidebar`, `SidebarItem`,
 * `SidebarLabel`, `PageHeader`, `Breadcrumbs`, `Dropdown` ni `Avatar` de
 * frappe-ui.
 *
 * La ganancia no es solo de stack: al ser marcado nuestro desaparecen los
 * `:deep([data-slot='sidebar-item'])` con `!important` que hacían falta para
 * revestir un componente ajeno. Es exactamente el argumento del estilo §1 para
 * shadcn — el aspecto lo ponen nuestros tokens en vez de pelearse con los de la
 * librería.
 *
 * Patrón del estilo §3.1: lateral de 14rem con cromo de marca fijo y contenido
 * desplazable aparte; la marca arriba, el usuario y la sesión abajo.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from 'frappe-ui'
import { Chart, Exit, Gauge, Layout, Moon, Search, Sun } from 'reicon-vue'
import AreaScroll from '@/components/ui/AreaScroll.vue'
import Avatar from '@/components/ui/Avatar.vue'
import EnlaceLateral from '@/components/ui/EnlaceLateral.vue'
import MenuDesplegable from '@/components/ui/MenuDesplegable.vue'
import Migas from '@/components/ui/Migas.vue'
import { AREAS } from '@/data/areas'
import { doctypesDeTrabajo, puede } from '@/composables/usePermisos'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const session = useSessionStore()
const { currentTheme, toggleTheme, setTheme } = useTheme()

// El producto inicia en claro; cada persona puede seleccionar oscuro y su
// preferencia queda persistida en localStorage.
onMounted(() => {
  if (!localStorage.getItem('theme')) setTheme('light')
})

const themeActionLabel = computed(() =>
  currentTheme.value === 'dark' ? 'Activar modo claro' : 'Activar modo oscuro',
)

// Activo institucional oficial. Sobre el cromo navy va la versión BLANCA
// directamente sobre el lateral: el estilo §3.1 es explícito en no añadir una
// tarjeta blanca solo para contenerlo, porque ese rectángulo ajeno fragmenta el
// cromo. La fuente autoritativa vive en ~/proyectos/upeu/branding/.
const upeuLogo = '/assets/sgc/media/login/upeu-logo-2026-white.svg'

// El menú solo ofrece lo que esta persona puede abrir. Antes se pintaban las
// 43 entradas para todo el mundo -- la misma lista para la DPGC que para un rol
// de solo lectura --, así que nadie deducía su ámbito mirando la pantalla. Un
// área cuyos items desaparecen entera se oculta también: una cabecera de
// sección sin nada debajo es ruido.
const areasVisibles = computed(() =>
  AREAS.map((area) => ({
    ...area,
    items: area.items.filter((i) => puede(i.doctype, 'read')),
  })).filter((area) => area.items.length > 0),
)

// Lo que esta persona EJECUTA, arriba del todo. Filtrar por lectura no bastaba:
// medido en producción el 2026-08-24, un Dueño de Proceso trabajaba 4 DocTypes y
// veía 36, un Auditor trabajaba 3 y veía 39. Y no es que sobren permisos —un
// auditor tiene que poder leerlo todo—: es que el menú respondía a «qué puedo
// ver» cuando la pregunta al entrar es «qué me toca hacer».
const misTareas = computed(() => {
  const trabajo = doctypesDeTrabajo()
  if (!trabajo.length) return []
  const items = []
  for (const area of AREAS) {
    for (const item of area.items) {
      if (trabajo.includes(item.doctype) && puede(item.doctype, 'read')) {
        items.push({ ...item, icon: item.icon || area.icon })
      }
    }
  }
  return items
})

// El resto del sistema sigue estando, pero pliega. Quien necesita explorarlo
// entero —el auditor, la DPGC— lo abre; quien viene a hacer una cosa ya no tiene
// que leer diez cabeceras para encontrarla. Abierto por defecto si esta persona
// no ejecuta nada: sin bloque de trabajo, plegar el resto la dejaría en blanco.
const restoAbierto = ref(false)
onMounted(() => {
  restoAbierto.value = misTareas.value.length === 0
})

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

const userMenu = [{ label: 'Cerrar sesión', icon: Exit, onClick: () => session.logout() }]
</script>

<template>
  <div class="sgc-shell flex h-screen w-full bg-fondo text-tinta">
    <!-- ── Lateral: 14rem, cromo de marca fijo, contenido desplazable aparte ── -->
    <aside
      class="sgc-app-sidebar flex w-56 shrink-0 flex-col border-r border-black/20"
      data-theme="dark"
    >
      <!-- La marca es el acceso a Inicio. Feedback de press sutil: es navegación
           ocasional, no una acción que se repita cientos de veces al día. -->
      <!-- `aria-current-value="false"` no es un adorno. RouterLink marca
           `aria-current="page"` por su cuenta al coincidir la ruta, y como la
           marca tambien lleva a Inicio, en la portada habia DOS elementos
           anunciandose como pagina actual: el logo y la entrada «Inicio». La
           marca es un atajo, no la posicion en el menu. Detectado leyendo el DOM
           renderizado; no lo ve ningun verificador ni el build. -->
      <RouterLink
        :to="{ name: 'Home' }"
        aria-current-value="false"
        class="brand-header group block shrink-0 px-4 pb-3 pt-4 focus-visible:outline-none"
      >
        <div
          class="brand-card flex items-center gap-3 rounded-xl px-1 py-1.5 transition-[transform,background-color] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] group-hover:bg-white/5 group-active:scale-[0.98]"
        >
          <img
            :src="upeuLogo"
            alt="Universidad Peruana Unión"
            class="h-9 w-auto max-w-[9.5rem] object-contain"
          />
        </div>
        <div class="mt-3 px-0.5">
          <div class="flex items-center gap-1.5">
            <span class="h-3 w-1 rounded-full bg-marca-secundaria-500" aria-hidden="true" />
            <span class="text-[10px] font-bold uppercase tracking-[0.15em] text-white/75">
              Sistema de Gestión de la Calidad
            </span>
          </div>
        </div>
      </RouterLink>

      <AreaScroll class="min-h-0 flex-1" viewport-class="px-3 pt-1 pb-10">
        <nav class="space-y-0.5" aria-label="Principal">
          <EnlaceLateral :to="{ name: 'Home' }">
            <template #icono><Layout :size="16" aria-hidden="true" /></template>
            Inicio
          </EnlaceLateral>
          <EnlaceLateral :to="{ name: 'TableroEjecutivo' }">
            <template #icono><Gauge :size="16" aria-hidden="true" /></template>
            Tablero ejecutivo
          </EnlaceLateral>
          <EnlaceLateral :to="{ name: 'Tablero' }">
            <template #icono><Chart :size="16" aria-hidden="true" /></template>
            Tablero de indicadores
          </EnlaceLateral>
        </nav>

        <!-- Lo que esta persona ejecuta. Va primero porque es a lo que viene. -->
        <div v-if="misTareas.length" class="mt-5">
          <h3
            class="flex h-7 items-center px-2 text-[0.68rem] font-bold uppercase tracking-[0.08em] text-white/50"
          >
            Tu trabajo
          </h3>
          <nav class="mt-0.5 space-y-0.5" aria-label="Tu trabajo">
            <EnlaceLateral
              v-for="item in misTareas"
              :key="`trabajo-${item.doctype}`"
              :to="{ name: 'DoctypeList', params: { doctype: item.doctype } }"
            >
              <template #icono>
                <component :is="item.icon" :size="16" aria-hidden="true" />
              </template>
              {{ item.label }}
            </EnlaceLateral>
          </nav>
        </div>

        <!-- Y el sistema entero, plegado: está, pero no estorba. -->
        <button
          v-if="misTareas.length"
          type="button"
          class="mt-5 flex h-7 w-full items-center justify-between px-2 text-[0.68rem] font-bold uppercase tracking-[0.08em] text-white/50 transition-colors hover:text-white/80"
          :aria-expanded="restoAbierto"
          @click="restoAbierto = !restoAbierto"
        >
          <span>Todo el sistema</span>
          <span aria-hidden="true">{{ restoAbierto ? '−' : '+' }}</span>
        </button>

        <div
          v-for="area in areasVisibles"
          v-show="restoAbierto || !misTareas.length"
          :key="area.label"
          class="mt-5"
        >
          <!-- Etiqueta de sección: pequeña, no un enlace ni un titular (§3.1). -->
          <h3
            class="flex h-7 items-center px-2 text-[0.68rem] font-bold uppercase tracking-[0.08em] text-white/50"
          >
            {{ area.label }}
          </h3>
          <nav class="mt-0.5 space-y-0.5" :aria-label="area.label">
            <EnlaceLateral
              v-for="item in area.items"
              :key="item.doctype"
              :to="{ name: 'DoctypeList', params: { doctype: item.doctype } }"
            >
              <template #icono>
                <component :is="item.icon || area.icon" :size="16" aria-hidden="true" />
              </template>
              {{ item.label }}
            </EnlaceLateral>
          </nav>
        </div>
      </AreaScroll>

      <div class="mt-auto flex items-center gap-2 border-t border-white/10 p-3">
        <MenuDesplegable :opciones="userMenu" alineacion="start">
          <button
            type="button"
            class="flex w-full items-center gap-2 rounded-xl p-1.5 text-left transition-colors duration-150 hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color-mix(in_srgb,var(--color-marca-secundaria-500)_60%,transparent)] data-[state=open]:bg-white/10"
          >
            <Avatar :nombre="session.displayName" tamano="sm" />
            <span class="flex-1 truncate text-sm text-white/85">{{ session.displayName }}</span>
          </button>
        </MenuDesplegable>
      </div>
    </aside>

    <!-- ── Contenido ── -->
    <div class="flex min-w-0 flex-1 flex-col">
      <header class="sgc-app-header flex shrink-0 items-center justify-between gap-4 px-5 py-3">
        <Migas :items="breadcrumbs" />
        <div class="flex items-center gap-3">
          <div
            class="hidden items-center gap-2 rounded-md border border-borde-fuerte bg-superficie-2 px-3 py-1.5 text-sm text-tinta-tenue sm:flex"
            title="Búsqueda global — próximamente"
          >
            <Search :size="16" aria-hidden="true" />
            <span>Buscar en el sistema…</span>
          </div>
          <button
            type="button"
            class="sgc-theme-toggle flex size-9 items-center justify-center rounded-md border border-borde-fuerte bg-superficie text-tinta-suave"
            :aria-label="themeActionLabel"
            :title="themeActionLabel"
            @click="toggleTheme"
          >
            <component :is="currentTheme === 'dark' ? Sun : Moon" :size="16" aria-hidden="true" />
          </button>
          <MenuDesplegable :opciones="userMenu">
            <button
              type="button"
              class="rounded-full transition-opacity duration-150 hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color-mix(in_srgb,var(--color-marca-primaria-500)_40%,transparent)]"
              :aria-label="`Sesión de ${session.displayName}`"
            >
              <Avatar :nombre="session.displayName" tamano="lg" />
            </button>
          </MenuDesplegable>
        </div>
      </header>

      <main class="min-h-0 flex-1 overflow-y-auto">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
/* Ya no hacen falta los `:deep([data-slot='sidebar-item'])` con `!important`:
   el marcado del lateral es propio y su estado activo lo pone EnlaceLateral. */

/* La marca es un enlace ocasional, así que un feedback sutil de press es
   apropiado; se anula bajo prefers-reduced-motion. */
@media (prefers-reduced-motion: reduce) {
  .brand-card {
    transition: box-shadow 200ms ease;
  }
  .brand-header:active .brand-card {
    transform: none;
  }
}
</style>
