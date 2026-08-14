<script setup>
/**
 * Selector con búsqueda. Sobre las primitivas Combobox de reka-ui.
 *
 * ES EL ÚNICO COMPONENTE QUE NO ENVUELVE UNO DEL REGISTRO, y conviene dejar
 * escrito el porqué para que nadie lo "arregle" migrándolo.
 *
 * El combobox de shadcn-vue se compone de `Popover` + `Command`, y `Command`
 * FILTRA EN CLIENTE de forma incondicional (`useFilter` + `filterItems`, sin
 * prop para desactivarlo). Aquí las opciones llegan YA filtradas por el servidor
 * de Frappe, que busca a la vez por `name` y por título. Pasarlas por su
 * `contains` volvería a cribarlas y escondería resultados válidos — un documento
 * encontrado por su título desaparecería por no contener el texto en su `name`.
 * Sería una pérdida de datos silenciosa, no una diferencia estética.
 *
 * La primitiva SÍ es la misma que usa shadcn (reka-ui), así que el teclado
 * —flechas, Enter, Esc—, el foco y la accesibilidad vienen igual de resueltos.
 * El aspecto se escribe con los mismos tokens semánticos que los componentes del
 * registro (`bg-popover`, `border-input`…), de modo que no desentona.
 *
 * Emite `update:query` para que el llamador busque en el servidor: el componente
 * no sabe de dónde salen las opciones y sirve igual para una lista fija que para
 * un Link a un DocType.
 */
import { computed } from 'vue'
import {
  ComboboxRoot, ComboboxAnchor, ComboboxInput, ComboboxTrigger,
  ComboboxContent, ComboboxViewport, ComboboxItem, ComboboxItemIndicator, ComboboxEmpty,
} from 'reka-ui'
import { AngleDown, Check, Loader } from 'reicon-vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: { type: [String, Number], default: null },
  options: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  placeholder: { type: String, default: 'Seleccionar…' },
})
const emit = defineEmits(['update:modelValue', 'update:query'])

const normalizadas = computed(() =>
  props.options.map((o) => (typeof o === 'object' ? o : { label: String(o), value: o })),
)
const etiquetaActual = computed(
  () => normalizadas.value.find((o) => o.value === props.modelValue)?.label ?? '',
)
</script>

<template>
  <ComboboxRoot
    :model-value="modelValue"
    :disabled="disabled"
    class="relative"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <ComboboxAnchor
      :class="cn('border-input flex h-11 w-full items-center gap-2 rounded-xl border bg-transparent px-3 text-sm',
         'transition-[color,box-shadow] focus-within:border-ring focus-within:ring-ring/50 focus-within:ring-3',
         disabled && 'opacity-60')"
    >
      <ComboboxInput
        class="flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
        :placeholder="placeholder"
        :display-value="() => etiquetaActual"
        @input="emit('update:query', $event.target.value)"
      />
      <Loader v-if="loading" :size="16" class="animate-spin text-tinta-tenue" aria-hidden="true" />
      <ComboboxTrigger v-else aria-label="Abrir opciones">
        <AngleDown :size="16" class="text-tinta-tenue" aria-hidden="true" />
      </ComboboxTrigger>
    </ComboboxAnchor>

    <ComboboxContent
      :class="[
        'absolute z-50 mt-1 w-full overflow-hidden rounded-xl border bg-popover text-popover-foreground shadow-md',
        // Entra con ease-out y desde scale(0.97), nunca desde 0: nada aparece de
        // la nada. Y desde su disparador, no desde el centro (estilo §6).
        'origin-[var(--reka-combobox-content-transform-origin)]',
        'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
        'duration-150 ease-out motion-reduce:animate-none',
      ]"
      position="popper"
    >
      <ComboboxViewport class="max-h-60 overflow-y-auto p-1">
        <ComboboxEmpty class="px-3 py-2 text-sm text-muted-foreground">Sin resultados</ComboboxEmpty>
        <ComboboxItem
          v-for="o in normalizadas"
          :key="o.value"
          :value="o.value"
          class="flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-sm text-tinta data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground data-[highlighted]:outline-none"
        >
          <span class="min-w-0">
            <span class="block truncate">{{ o.label }}</span>
            <!-- LinkField pasa `description` (p.ej. el titulo del documento);
                 sin esto se perdia informacion que antes si se veia. -->
            <span v-if="o.description" class="block truncate text-xs text-tinta-tenue">{{ o.description }}</span>
          </span>
          <ComboboxItemIndicator>
            <Check :size="16" class="text-primary" aria-hidden="true" />
          </ComboboxItemIndicator>
        </ComboboxItem>
      </ComboboxViewport>
    </ComboboxContent>
  </ComboboxRoot>
</template>
