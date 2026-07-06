import { ref, watchEffect } from 'vue'

// Metadata de un DocType (campos, tipos, opciones) vía el endpoint que usa el
// propio Frappe Desk (frappe.desk.form.load.getdoctype) — a diferencia de leer
// el doc "DocType" directamente (/api/v2/document/DocType/<x>), este método es
// seguro para CUALQUIER usuario con acceso al doctype de negocio, no solo
// System Manager/Administrator (el doc DocType en sí tiene permisos propios
// más restrictivos). No encaja en el envelope v2 de useCall (no retorna un
// valor, muta frappe.response), así que se hace un fetch crudo.
const cache = new Map()

export function useDoctypeMeta(doctype) {
  const meta = ref(cache.get(doctype) || null)
  const loading = ref(!meta.value)
  const error = ref(null)

  watchEffect(async () => {
    const dt = typeof doctype === 'function' ? doctype() : doctype
    if (!dt || cache.has(dt)) {
      meta.value = cache.get(dt) || null
      loading.value = false
      return
    }
    loading.value = true
    try {
      const res = await fetch(
        `/api/method/frappe.desk.form.load.getdoctype?doctype=${encodeURIComponent(dt)}`,
        { credentials: 'same-origin' },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const body = await res.json()
      const doc = (body.docs || []).find((d) => d.name === dt && d.doctype === 'DocType')
      if (!doc) throw new Error(`Metadata de "${dt}" no encontrada`)
      const fields = (doc.fields || []).filter(
        (f) => !['Section Break', 'Column Break', 'Tab Break'].includes(f.fieldtype),
      )
      const value = {
        doctype: dt,
        fields,
        titleField: doc.title_field || null,
        searchFields: (doc.search_fields || '').split(',').map((s) => s.trim()).filter(Boolean),
      }
      cache.set(dt, value)
      meta.value = value
    } catch (e) {
      error.value = e
    } finally {
      loading.value = false
    }
  })

  return { meta, loading, error }
}
