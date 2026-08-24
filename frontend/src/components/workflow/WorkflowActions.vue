<script setup>
import { computed, ref, watch } from 'vue'
import { useCall } from 'frappe-ui'
import Boton from '@/components/ui/Boton.vue'
import Alerta from '@/components/ui/Alerta.vue'
import { avisar } from '@/composables/useAvisos'
import { mensajeDeError } from '@/lib/mensajesFrappe'

const props = defineProps({
  document: { type: Object, required: true },
  stateField: { type: String, default: 'estado' },
})

const emit = defineEmits(['completed'])

const transitions = useCall({
  url: '/api/v2/method/frappe.model.workflow.get_transitions',
  method: 'POST',
  immediate: false,
})

const apply = useCall({
  url: '/api/v2/method/frappe.model.workflow.apply_workflow',
  method: 'POST',
  immediate: false,
})

// De quién es el turno. `get_transitions` solo devuelve MIS acciones, así que
// cuando el documento espera a otro rol la pantalla se quedaba muda: «no hay
// acciones disponibles» es cierto e inútil. En un flujo con segregación de
// funciones eso pasa en la mitad de los pasos, por diseño.
const siguiente = useCall({
  url: '/api/v2/method/sgc.siguiente_paso.de',
  method: 'POST',
  immediate: false,
})

const esperandoA = computed(() => siguiente.data?.de_otros || [])
const esFinal = computed(() => Boolean(siguiente.data?.final))

const activeAction = ref('')
const currentState = computed(() => props.document?.[props.stateField] || 'Sin estado')
const actions = computed(() => transitions.data || [])
// El texto lo pone Frappe; una cancelación no se enseña. Ver
// `lib/mensajesFrappe`.
const errorMessage = computed(
  () => mensajeDeError(apply.error, '') || mensajeDeError(transitions.error, '') || '',
)

const ACTION_LABELS = {
  'Iniciar evaluacion': 'Iniciar evaluación',
  'Enviar a revision': 'Enviar a revisión',
  'Devolver a evaluacion': 'Devolver a evaluación',
  'Analizar causa': 'Analizar causa',
  'Enviar a verificacion': 'Enviar a verificación',
  'Cerrar eficaz': 'Cerrar eficaz',
  'Cerrar no eficaz': 'Cerrar no eficaz',
  'Reabrir tratamiento': 'Reabrir tratamiento',
}

function actionLabel(action) {
  return ACTION_LABELS[action] || action
}

function isSecondary(action) {
  return /^(Devolver|Reabrir|Observar)/.test(action)
}

function serialized(document = props.document) {
  return JSON.stringify(document)
}

async function loadTransitions(document = props.document) {
  if (!document?.doctype || !document?.name) return null
  siguiente.submit({ doctype: document.doctype, name: document.name })
  return transitions.submit({ doc: serialized(document) })
}

async function applyAction(action) {
  if (!action || activeAction.value) return
  activeAction.value = action
  try {
    const updated = await apply.submit({
      doc: serialized(),
      action,
    })
    if (!updated || apply.error) return
    avisar(`${actionLabel(action)}: hecho`, 'exito', {
      detalle: `El documento pasa a «${updated[props.stateField]}».`,
    })
    emit('completed', updated)
    await loadTransitions(updated)
  } finally {
    activeAction.value = ''
  }
}

watch(
  () => [props.document?.doctype, props.document?.name, props.document?.[props.stateField]],
  () => loadTransitions(),
  { immediate: true },
)
</script>

<template>
  <section class="workflow-actions" aria-label="Acciones de flujo">
    <div class="workflow-state">
      <span class="workflow-state__label">Estado actual</span>
      <strong class="workflow-state__value">{{ currentState }}</strong>
    </div>

    <div class="workflow-actions__controls">
      <span v-if="transitions.loading && !transitions.data" class="text-sm text-tinta-tenue">
        Consultando acciones…
      </span>
      <template v-else-if="actions.length">
        <Boton
          v-for="transition in actions"
          :key="transition.action"
          :variante="isSecondary(transition.action) ? 'secundario' : 'primario'"
          :cargando="activeAction === transition.action"
          :deshabilitado="Boolean(activeAction)"
          @click="applyAction(transition.action)"
        >
          {{ actionLabel(transition.action) }}
        </Boton>
      </template>
      <p v-else-if="esFinal" class="text-sm text-tinta-tenue">
        Este documento terminó su recorrido: no hay más acciones.
      </p>
      <p v-else-if="esperandoA.length" class="text-sm text-tinta-tenue">
        Ahora le toca a
        <template v-for="(t, i) in esperandoA" :key="t.accion">
          <strong>{{ t.rol }}</strong> ({{ actionLabel(t.accion) }}){{
            i < esperandoA.length - 1 ? ' o a ' : ''
          }}</template>. Tú no tienes nada pendiente aquí.
      </p>
      <p v-else class="text-sm text-tinta-tenue">
        No hay acciones disponibles para tu rol en este estado.
      </p>
    </div>

    <Alerta v-if="errorMessage" :message="errorMessage" />
  </section>
</template>

<style scoped>
.workflow-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.875rem 1rem;
  padding: 1rem;
  border: 1px solid var(--color-borde);
  border-radius: 0.875rem;
  background: var(--color-superficie);
}

.workflow-state {
  display: grid;
  min-width: 8.75rem;
  gap: 0.125rem;
}

.workflow-state__label {
  color: var(--color-tinta-suave);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.workflow-state__value {
  color: var(--color-tinta);
  font-size: 0.9375rem;
}

.workflow-actions__controls {
  display: flex;
  flex: 1 1 22rem;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.625rem;
}

@media (max-width: 40rem) {
  .workflow-actions,
  .workflow-actions__controls {
    align-items: stretch;
  }

  .workflow-actions__controls > :deep(button) {
    width: 100%;
    justify-content: center;
  }
}
</style>
