<script setup>
import { computed } from 'vue'
import { Combobox, useCall } from 'frappe-ui'

// "Nivel Escala" está marcado istable=1 en el DocType (heredado del diseño
// original) — eso hace que TODOS los endpoints genéricos de listado/búsqueda
// (frappe.client.get_list, frappe.desk.search.search_link) le recorten los
// campos extra y solo devuelvan `name` (limitación conocida del query builder
// de Frappe para doctypes de tabla consultados como documento independiente).
// Se resuelve con un endpoint propio (sgc.api.get_niveles_escala) que sí trae
// sigla/etiqueta. Es una escala fija de 3 niveles (NL/L/LP): se trae completa
// una vez, sin necesidad de búsqueda incremental.
defineProps({ modelValue: { type: String, default: null } })
defineEmits(['update:modelValue'])

const niveles = useCall({
  url: '/api/v2/method/sgc.api.get_niveles_escala',
  cacheKey: ['nivel-escala', 'todos'],
})

const options = computed(() =>
  (niveles.data || []).map((n) => ({ label: `${n.sigla} · ${n.etiqueta}`, value: n.name })),
)
</script>

<template>
  <Combobox
    :model-value="modelValue"
    :options="options"
    :loading="niveles.loading"
    placeholder="Seleccionar nivel…"
    class="w-full"
    @update:model-value="$emit('update:modelValue', $event)"
  />
</template>
