<script setup>
/**
 * Campo de formulario rotulado. Reemplaza al `FormControl` de frappe-ui.
 *
 * UN SOLO patrón de campo para input/textarea/select/checkbox (estilo §5): Pulso
 * DTI llegó a tener dos juegos de clases y se descolgaban entre sí. Aquí el
 * aspecto lo pone `.campo`, declarado una vez en sciback-core.css.
 *
 * Reglas de la casa que este componente hace cumplir por defecto:
 *  · Etiqueta SIEMPRE, con `for`/`id` reales. El placeholder no es etiqueta.
 *  · Anillo de foco visible y de marca — nunca `outline:none` sin reemplazo.
 *  · Error inline junto al campo, con `role="alert"`.
 */
import { computed, useId } from 'vue'
import { cn } from '@/lib/cn'

const props = defineProps({
  type: { type: String, default: 'text' }, // text|number|textarea|select|checkbox|date|datetime
  // Los `defineModel` de los campos arrancan en `null` cuando el DocType no trae
  // valor. Vue no valida el tipo si el valor es null, asi que no hace falta
  // declararlo; se anota para que nadie 'arregle' el default a null por error.
  modelValue: { type: [String, Number, Boolean], default: '' },
  label: { type: String, default: undefined },
  options: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  placeholder: { type: String, default: undefined },
  error: { type: String, default: '' },
  required: { type: Boolean, default: false },
  // Alto del textarea en filas. Sin esta prop el `rows` del llamador caia por
  // fallthrough en el <div> raiz y no hacia nada — lo detectaron 3 ficheros.
  rows: { type: [Number, String], default: null },
})
const emit = defineEmits(['update:modelValue'])

const id = useId()
const errorId = computed(() => `${id}-error`)

const esCheckbox = computed(() => props.type === 'checkbox')
const etiquetaTipo = computed(() => (props.type === 'datetime' ? 'datetime-local' : props.type))

function alCambiar(e) {
  emit('update:modelValue', esCheckbox.value ? e.target.checked : e.target.value)
}

// `h-11` = 44px: el mínimo de zona táctil de WCAG 2.5.5 (estilo §2).
const claseControl = computed(() =>
  cn('campo w-full rounded-xl px-3 text-sm',
     props.type === 'textarea' ? (props.rows ? 'py-2' : 'min-h-24 py-2') : 'h-11'),
)
</script>

<template>
  <div :class="cn('flex flex-col gap-1.5', esCheckbox && 'flex-row items-center gap-2')">
    <label
      v-if="label && !esCheckbox"
      :for="id"
      class="text-xs font-semibold uppercase tracking-wide text-tinta-tenue"
    >
      {{ label }}<span v-if="required" class="text-peligro" aria-hidden="true"> *</span>
    </label>

    <textarea
      v-if="type === 'textarea'"
      :id="id"
      :value="modelValue"
      :disabled="disabled"
      :placeholder="placeholder"
      :required="required"
      :rows="rows ?? undefined"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="error ? errorId : undefined"
      :class="claseControl"
      @input="alCambiar"
    />

    <select
      v-else-if="type === 'select'"
      :id="id"
      :value="modelValue"
      :disabled="disabled"
      :required="required"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="error ? errorId : undefined"
      :class="claseControl"
      @change="alCambiar"
    >
      <option v-for="o in options" :key="o.value ?? o" :value="o.value ?? o">
        {{ o.label ?? o }}
      </option>
    </select>

    <input
      v-else
      :id="id"
      :type="etiquetaTipo"
      :value="esCheckbox ? undefined : modelValue"
      :checked="esCheckbox ? Boolean(modelValue) : undefined"
      :disabled="disabled"
      :placeholder="placeholder"
      :required="required"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="error ? errorId : undefined"
      :class="esCheckbox ? 'size-4 rounded border-borde-fuerte accent-marca-primaria-700' : claseControl"
      @input="alCambiar"
    />

    <label v-if="label && esCheckbox" :for="id" class="text-sm text-tinta">{{ label }}</label>

    <p v-if="error" :id="errorId" role="alert" class="text-xs text-peligro">{{ error }}</p>
  </div>
</template>
