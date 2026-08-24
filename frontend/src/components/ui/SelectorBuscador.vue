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
import { computed, ref } from 'vue'
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

// Apertura controlada: hace falta para poder abrir al enfocar y al pulsar, no
// solo al teclear.
const abierto = ref(false)

const normalizadas = computed(() =>
  props.options.map((o) => (typeof o === 'object' ? o : { label: String(o), value: o })),
)
const etiquetaActual = computed(
  () => normalizadas.value.find((o) => o.value === props.modelValue)?.label ?? '',
)
</script>

<template>
  <ComboboxRoot
    v-model:open="abierto"
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
      <!-- Abre al PULSAR, no solo al escribir. Comprobado el 2026-08-24 con
           alguien usándolo: pulsó, no pasó nada, y concluyó —con razón— que la
           búsqueda no funcionaba. Un campo con una flecha ⌄ al lado promete que
           al pulsarlo se despliega; si no lo hace, la promesa es falsa y no hay
           forma de saber que hay que escribir a ciegas. -->
      <!-- `v-model:open` va SOLO en la raíz. Ponerlo también aquí hacía que
           cada tecla forzara un redibujado del input y el texto se quedara
           congelado: se escribía «gesti» y el retroceso no borraba nada.
           Comprobado con teclado real el 2026-08-24.
           `display-value` solo se aplica cuando hay algo elegido; mientras se
           escribe, manda lo tecleado. -->
      <ComboboxInput
        class="flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
        :placeholder="placeholder"
        :display-value="() => (modelValue ? etiquetaActual : undefined)"
        @focus="abierto = true"
        @click="abierto = true"
        @input="emit('update:query', $event.target.value)"
      />
      <Loader v-if="loading" :size="16" class="animate-spin text-tinta-tenue" aria-hidden="true" />
      <ComboboxTrigger v-else aria-label="Abrir opciones">
        <AngleDown :size="16" class="text-tinta-tenue" aria-hidden="true" />
      </ComboboxTrigger>
    </ComboboxAnchor>

    <ComboboxContent
      :class="[
        // Posicionado contra `ComboboxRoot`, que es `relative`. Sin el modo
        // popper de reka: con él, el contenido se monta en un envoltorio propio
        // de ancho 0, este w-full medía 0, y el desplegable se dibujaba como una
        // LINEA VERTICAL de 2px con las opciones dentro, invisibles. Comprobado
        // en produccion el 2026-08-24. Su variable de ancho tampoco sirve aqui:
        // mide el disparador (la flecha, 26px), no el campo.
        'absolute z-50 mt-1 w-full overflow-hidden rounded-xl border bg-popover text-popover-foreground shadow-md',
        // Entra con ease-out y desde scale(0.97), nunca desde 0: nada aparece de
        // la nada. Y desde su disparador, no desde el centro (estilo §6).
        'origin-[var(--reka-combobox-content-transform-origin)]',
        'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
        'duration-150 ease-out motion-reduce:animate-none',
      ]"
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
