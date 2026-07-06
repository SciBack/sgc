<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Avatar,
  Breadcrumbs,
  DesktopShell,
  Dropdown,
  PageHeader,
  ScrollArea,
  Sidebar,
  SidebarHeader,
  SidebarItem,
  SidebarLabel,
} from 'frappe-ui'
import { AREAS } from '@/data/areas'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const session = useSessionStore()

const breadcrumbs = computed(() => {
  const items = [{ label: 'Inicio', route: { name: 'Home' } }]
  if (route.name === 'DoctypeList') {
    const area = AREAS.find((a) => a.items.some((i) => i.doctype === route.params.doctype))
    const item = area?.items.find((i) => i.doctype === route.params.doctype)
    if (area) items.push({ label: area.label })
    if (item) items.push({ label: item.label })
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
</script>

<template>
  <div class="h-screen w-full bg-surface-base text-ink-gray-9">
    <DesktopShell>
      <template #sidebar>
        <Sidebar width="15rem" class="border-r">
          <SidebarHeader title="SGC · UPeU" subtitle="Gestión de la Calidad" logo="/files/upeu-favicon.ico" />

          <ScrollArea class="min-h-0 flex-1" viewport-class="px-2 pt-0.5 pb-10">
            <nav class="space-y-0.5">
              <SidebarItem :to="{ name: 'Home' }">
                <template #prefix>
                  <span class="lucide-layout-dashboard size-4" aria-hidden="true" />
                </template>
                <span class="flex-1 truncate text-sm">Inicio</span>
              </SidebarItem>
            </nav>

            <div v-for="area in AREAS" :key="area.label" class="mt-4">
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

          <div class="mt-auto flex items-center gap-2 border-t p-2">
            <Dropdown :options="userMenu">
              <template #default="{ open }">
                <button
                  class="flex w-full items-center gap-2 rounded p-1.5 text-left hover:bg-surface-gray-1"
                  :class="{ 'bg-surface-gray-1': open }"
                >
                  <Avatar :label="session.user" size="sm" />
                  <span class="flex-1 truncate text-sm text-ink-gray-8">{{ session.user }}</span>
                </button>
              </template>
            </Dropdown>
          </div>
        </Sidebar>
      </template>

      <PageHeader>
        <Breadcrumbs :items="breadcrumbs" />
      </PageHeader>

      <router-view />
    </DesktopShell>
  </div>
</template>
