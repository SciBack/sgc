import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Une clases resolviendo conflictos de Tailwind: la última gana.
 *  Sin esto, `class="p-2"` pasada desde fuera no puede sobreescribir el `p-4`
 *  interno de un componente — quedan las dos y decide el orden del CSS, no el
 *  del autor.
 *
 *  Vive en `lib/utils` y no en `lib/cn` porque es la ruta que declara
 *  `components.json` y la que importan los componentes traídos con
 *  `shadcn-vue add`. Tener dos copias era garantizar que se separaran. */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
