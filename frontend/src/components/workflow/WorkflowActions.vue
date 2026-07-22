<script setup>
import { computed, ref, watch } from 'vue'
import { Button, ErrorMessage, useCall } from 'frappe-ui'

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

const activeAction = ref('')
const currentState = computed(() => props.document?.[props.stateField] || 'Sin estado')
const actions = computed(() => transitions.data || [])
const errorMessage = computed(() => apply.error?.message || transitions.error?.message || '')

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
      <span v-if="transitions.loading && !transitions.data" class="text-p-sm text-ink-gray-5">
        Consultando acciones…
      </span>
      <template v-else-if="actions.length">
        <Button
          v-for="transition in actions"
          :key="transition.action"
          :variant="isSecondary(transition.action) ? 'outline' : 'solid'"
          :class="isSecondary(transition.action) ? 'btn-press' : 'sb-primary-action btn-press'"
          :loading="activeAction === transition.action"
          :disabled="Boolean(activeAction)"
          @click="applyAction(transition.action)"
        >
          {{ actionLabel(transition.action) }}
        </Button>
      </template>
      <p v-else class="text-p-sm text-ink-gray-5">
        No hay acciones disponibles para tu rol en este estado.
      </p>
    </div>

    <ErrorMessage v-if="errorMessage" :message="errorMessage" />
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
