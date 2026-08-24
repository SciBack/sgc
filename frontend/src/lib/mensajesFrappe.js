/**
 * El mensaje de error lo escribe Frappe; aquí solo se lee.
 *
 * Frappe devuelve en `_server_messages` un JSON con el texto ya redactado,
 * traducido y con el nombre legible del campo. Para un obligatorio que falta
 * manda literalmente:
 *
 *   «Error: falta el valor para Documento Controlado: Tipo de documento»
 *
 * La SPA lo estaba descartando para mostrar un genérico propio —«No se pudo
 * crear el registro»— que dice menos y además se desincroniza: cada validación
 * nueva del servidor nace muda en la interfaz. Es la misma trampa en la que se
 * cae al reimplementar cualquier cosa que Frappe ya resuelve.
 *
 * Regla: el servidor es la fuente del mensaje. Solo se pone texto propio cuando
 * NO viene ninguno, y en ese caso se dice lo poco que se sabe con honestidad.
 */

/** Extrae los mensajes que Frappe adjunta a la respuesta, en orden. */
export function mensajesDelServidor(err) {
  const crudos = err?._server_messages ?? err?.response?._server_messages
  if (!crudos) return []
  let lista = crudos
  if (typeof lista === 'string') {
    try {
      lista = JSON.parse(lista)
    } catch {
      return [limpiar(lista)]
    }
  }
  if (!Array.isArray(lista)) return []
  return lista
    .map((m) => {
      if (typeof m !== 'string') return limpiar(m?.message)
      try {
        return limpiar(JSON.parse(m).message)
      } catch {
        return limpiar(m)
      }
    })
    .filter(Boolean)
}

/** Frappe manda HTML en sus mensajes (negritas, saltos); aquí se lee en texto. */
function limpiar(texto) {
  if (!texto) return ''
  return String(texto)
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

/** ¿Es una petición cancelada? No es un error: no se enseña. */
export function esCancelacion(err) {
  return /abort/i.test(String(err?.message || err?.name || ''))
}

/**
 * El mensaje que debe leer una persona, priorizando lo que dijo el servidor.
 *
 * `respaldo` solo se usa cuando el servidor no dijo nada aprovechable — un
 * fallo de red, por ejemplo.
 */
export function mensajeDeError(err, respaldo = 'No se pudo completar la operación.') {
  if (!err || esCancelacion(err)) return ''

  const delServidor = mensajesDelServidor(err)
  if (delServidor.length) return delServidor.join(' · ')

  // Un 403 llega a menudo sin mensaje: se dice lo que significa, no un genérico.
  const tipo = String(err?.exc_type || err?.exception || '')
  const status = err?.status || err?.statusCode || err?.response?.status
  if (/PermissionError/i.test(tipo) || status === 403) {
    return 'No tienes permiso para esta operación. Corresponde a otro rol.'
  }

  const suelto = err?.messages?.[0] || err?.message || (typeof err === 'string' ? err : '')
  return limpiar(suelto) || respaldo
}
