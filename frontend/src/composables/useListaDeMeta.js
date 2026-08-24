/**
 * Columnas y filtros de una lista, derivados del meta del DocType.
 *
 * Frappe ya declara ambas cosas: `in_list_view` dice qué columnas enseñar e
 * `in_standard_filter` por qué se filtra. La lista pedía en su lugar dos campos
 * fijos —`name` y `modified`— para los 39 DocTypes, así que en «Proceso» se veía
 * `S04` y una fecha cuando el sistema tenía escrito que quisiera ver código,
 * nombre y nivel, y filtrar por nivel y estado.
 *
 * Derivarlo del meta significa que cuando Calidad decida qué columna importa,
 * se marca en el DocType y aparece: no hay que tocar código ni configurar
 * pantalla por pantalla.
 */

/** Columnas a mostrar. Si el DocType no declara ninguna, se cae a lo mínimo. */
export function columnasDeMeta(meta) {
  const campos = (meta?.fields || []).filter((f) => f.in_list_view && !f.hidden)
  if (!campos.length) {
    return [{ key: 'name', label: 'Registro' }]
  }
  // `name` primero solo si NO es ya una de las columnas: en los DocTypes que se
  // nombran por su código (Proceso, Documento Controlado) repetirlo sería una
  // columna gemela.
  const columnas = campos.map((f) => ({
    key: f.fieldname,
    label: f.label || f.fieldname,
    fieldtype: f.fieldtype,
  }))
  const yaEstaElNombre = campos.some((f) => esElNombre(meta, f.fieldname))
  return yaEstaElNombre ? columnas : [{ key: 'name', label: 'Registro' }, ...columnas]
}

function esElNombre(meta, fieldname) {
  const auto = meta?.autoname || ''
  return auto === `field:${fieldname}`
}

/** Campos por los que el DocType declara que se filtra. */
export function filtrosDeMeta(meta) {
  return (meta?.fields || [])
    .filter((f) => f.in_standard_filter && !f.hidden)
    .map((f) => ({
      key: f.fieldname,
      label: f.label || f.fieldname,
      fieldtype: f.fieldtype,
      // Un Select trae sus opciones en el meta; un Link las busca en su DocType.
      opciones: f.fieldtype === 'Select'
        ? (f.options || '').split('\n').map((o) => o.trim()).filter(Boolean)
        : null,
      doctype: f.fieldtype === 'Link' ? f.options : null,
    }))
}

/** Campos que hay que pedirle al servidor: los de la tabla más `name`. */
export function camposAConsultar(columnas) {
  const claves = new Set(['name', 'modified'])
  for (const c of columnas) claves.add(c.key)
  return [...claves]
}
