import { useCall } from 'frappe-ui'

// Autocomplete de campos Link/Dynamic Link vía el buscador nativo de Frappe
// (respeta permisos y title_field/search_fields del doctype destino — el
// mismo endpoint que usa el Desk para sus campos de enlace). Sin cacheKey:
// es una búsqueda en vivo por texto, cachear por doctype serviría resultados
// obsoletos para queries distintas.
export function useLinkSearch(doctype) {
  const search = useCall({
    url: '/api/v2/method/frappe.desk.search.search_link',
    immediate: false,
  })

  function query(txt) {
    search.submit({ doctype, txt: txt || '' })
  }

  return { search, query }
}
