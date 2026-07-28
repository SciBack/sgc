<script setup>
/**
 * Campo de formulario rotulado. Envoltorio de `Input`/`Textarea`/`Checkbox`/
 * `Label` de shadcn-vue.
 *
 * Sigue siendo UN SOLO patrón de campo para todos los tipos (estilo §5): Pulso
 * DTI llegó a tener dos juegos de clases y se descolgaron entre sí. Lo que
 * cambia es que el aspecto ya no lo pone la clase `.campo` escrita a mano, sino
 * los componentes del registro — y con ellos llega `aria-invalid` con su anillo
 * rojo, que antes solo era un atributo sin consecuencia visual.
 *
 * Reglas de la casa que este componente sigue imponiendo por defecto:
 *  · ETIQUETA SIEMPRE, con `for`/`id` reales. El placeholder no es etiqueta.
 *  · ERROR INLINE junto al campo, con `role="alert"` y enlazado por
 *    `aria-describedby` — el anillo rojo solo no dice QUÉ está mal.
 *  · ALTURA 44px (`h-11`), el mínimo táctil de WCAG 2.5.5; el `Input` de shadcn
 *    trae 36. Y `rounded-xl` en vez de su `rounded-md`, como el resto de la casa.
 *
 * `select` no tiene equivalente directo utilizable aquí: el `Select` de shadcn
 * es un menú de reka-ui con su propio estado, no un `<select>` nativo, y este
 * componente se usa dentro de formularios generados donde el nativo basta y
 * pesa menos. Se mantiene nativo con el mismo aspecto.
 */
import { computed, useId } from 'vue'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

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

// 44px de alto y radio xl: las dos correcciones de la casa sobre lo que trae
// shadcn. Van por `class`, que `cn` resuelve a favor del llamador.
const CASA = 'h-11 rounded-xl text-sm'
</script>

<template>
  <div :class="cn('flex flex-col gap-1.5', esCheckbox && 'flex-row items-center gap-2')">
    <Label
      v-if="label && !esCheckbox"
      :for="id"
      class="text-xs font-semibold uppercase tracking-wide text-tinta-tenue"
    >
      {{ label }}<span v-if="required" class="text-peligro" aria-hidden="true"> *</span>
    </Label>

    <Textarea
      v-if="type === 'textarea'"
      :id="id"
      :model-value="modelValue"
      :disabled="disabled"
      :placeholder="placeholder"
      :required="required"
      :rows="rows ?? undefined"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="error ? errorId : undefined"
      :class="cn('rounded-xl text-sm', rows ? 'py-2' : 'min-h-24 py-2')"
      @update:model-value="emit('update:modelValue', $event)"
    />

    <!-- Nativo a proposito: ver la nota de cabecera. Se le da el mismo aspecto
         que al Input de shadcn para que no desentone en el mismo formulario. -->
    <select
      v-else-if="type === 'select'"
      :id="id"
      :value="modelValue"
      :disabled="disabled"
      :required="required"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="error ? errorId : undefined"
      :class="cn(
        'border-input w-full border bg-transparent px-3 outline-none transition-[color,box-shadow]',
        'focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-3',
        'aria-invalid:border-destructive aria-invalid:ring-destructive/20',
        'disabled:cursor-not-allowed disabled:opacity-50',
        CASA,
      )"
      @change="emit('update:modelValue', $event.target.value)"
    >
      <option v-for="o in options" :key="o.value ?? o" :value="o.value ?? o">
        {{ o.label ?? o }}
      </option>
    </select>

    <Checkbox
      v-else-if="esCheckbox"
      :id="id"
      :model-value="Boolean(modelValue)"
      :disabled="disabled"
      :required="required"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="error ? errorId : undefined"
      @update:model-value="emit('update:modelValue', $event)"
    />

    <Input
      v-else
      :id="id"
      :type="etiquetaTipo"
      :model-value="modelValue"
      :disabled="disabled"
      :placeholder="placeholder"
      :required="required"
      :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="error ? errorId : undefined"
      :class="CASA"
      @update:model-value="emit('update:modelValue', $event)"
    />

    <Label v-if="label && esCheckbox" :for="id" class="text-sm text-tinta">{{ label }}</Label>

    <p v-if="error" :id="errorId" role="alert" class="text-xs text-peligro">{{ error }}</p>
  </div>
</template>
