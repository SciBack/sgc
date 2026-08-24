/**
 * Avisos efímeros: confirmar que el servidor guardó, y decir qué pasa ahora.
 *
 * Antes no había ninguno. Se creaba un documento, la aplicación navegaba a su
 * ficha, y no aparecía nada: el mensaje «Guardado» del formulario existía pero
 * se perdía en la navegación. Quien lo usaba no sabía si el servidor había
 * grabado — comprobado con una persona real el 2026-08-24, cuyas palabras
 * fueron «no me dio ningún mensaje diciéndome que se realizó correctamente».
 *
 * Es un store minúsculo a propósito, sin dependencia nueva: el stack canónico
 * manda shadcn + Radix, y meter una librería de toasts por tres funciones sería
 * traerse su estética además de su código.
 *
 * Los avisos se van solos. Un error se queda más tiempo que un éxito porque hay
 * que leerlo, y `permanente` los deja hasta que alguien los cierre.
 */
import { reactive } from 'vue'

const DURACION = { exito: 4000, info: 6000, aviso: 8000, error: 10000 }
let siguienteId = 1

export const avisos = reactive([])

export function avisar(mensaje, tono = 'exito', { detalle = '', permanente = false } = {}) {
  if (!mensaje) return null
  const id = siguienteId++
  avisos.push({ id, mensaje, detalle, tono })
  if (!permanente) {
    setTimeout(() => cerrarAviso(id), DURACION[tono] ?? DURACION.info)
  }
  return id
}

export function cerrarAviso(id) {
  const i = avisos.findIndex((a) => a.id === id)
  if (i !== -1) avisos.splice(i, 1)
}

export function useAvisos() {
  return { avisos, avisar, cerrarAviso }
}
