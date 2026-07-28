import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Une clases resolviendo conflictos de Tailwind: la última gana.
 *  Sin esto, `class="p-2"` pasada desde fuera no puede sobreescribir el `p-4`
 *  interno de un componente — quedan las dos y decide el orden del CSS, no el
 *  del autor. Es el helper estándar del stack (clsx + tailwind-merge). */
export function cn(...clases) {
  return twMerge(clsx(clases))
}
