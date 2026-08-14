# Contrato de migración — clases frappe-ui → tokens canónicos

Medido el 2026-07-27 sobre `frontend/src`: **246 usos de 29 clases distintas en 14 ficheros**.

Son las utilidades del preset Tailwind de `frappe-ui` (`ink-*`, `surface-*`, `outline-*`). Conviven
con los tokens canónicos `--color-*` y con las escalas `marca-*`, o sea **tres sistemas a la vez**
— el mismo problema que el design system documenta para RIMS y QuipuQ.

> **Punto ciego del verificador:** `verificar-stack.mjs` solo avisó de 9 tokens `--sgc-*`, porque
> mira variables CSS. Estas 246 son **clases de utilidad que vienen de un preset**, así que no las
> ve ninguno de los cinco verificadores.

## Neutros y texto

| frappe-ui | canónico | Nota |
|---|---|---|
| `text-ink-gray-9`, `-8` | `text-tinta` | Texto principal |
| `text-ink-gray-7`, `-6` | `text-tinta-suave` | Secundario |
| `text-ink-gray-5`, `-4` | `text-tinta-tenue` | Terciario |
| `bg-surface-gray-1` | `bg-superficie-2` | Zona hundida |
| `bg-surface-gray-2`, `-3` | `bg-superficie-3` | Hover / zona más hundida |
| `bg-surface-gray-4` | `bg-superficie-3` | |
| `border-outline-gray-1` | `border-borde` | Divisor |
| `border-outline-gray-2` | `border-borde-fuerte` | Input |
| `divide-outline-gray-1` | `divide-borde` | |

## Estados como tinta

| frappe-ui | canónico |
|---|---|
| `text-ink-green-6` | `text-exito` |
| `text-ink-amber-7`, `-6` | `text-aviso` |
| `text-ink-red-5`, `-6` | `text-peligro` |

## Superficies sutiles de estado — la decisión

`bg-surface-red-1`, `bg-surface-amber-1`, `bg-surface-green-1` (y sus `-2`) son **fondos tenues**
de estado. **El canon no los tiene**: define `--color-exito/aviso/peligro` como valores de tinta,
y las superficies neutras `superficie-1/2/3`. No hay `--color-superficie-peligro`.

Dos salidas posibles:

1. **Añadir tokens nuevos al canon** — toca el design system y afecta a los cuatro productos.
2. **`color-mix` sobre el token de estado** — que es justo lo que el método ya bendice en
   [§1.4](../../../sciback/sciback-design-system/canonico/metodo.md#14-alfa-sobre-un-token):
   `color-mix(in srgb, var(--color-peligro) 10%, transparent)`.

**Se elige la 2.** No inventa vocabulario nuevo, respeta que SciBack es dueño de los estados, y
evita que cada producto proponga su propia escala de superficies de estado. Se expresa como clases
utilitarias declaradas una vez:

```css
.bg-exito-tenue   { background-color: color-mix(in srgb, var(--color-exito)   10%, transparent); }
.bg-aviso-tenue   { background-color: color-mix(in srgb, var(--color-aviso)   10%, transparent); }
.bg-peligro-tenue { background-color: color-mix(in srgb, var(--color-peligro) 10%, transparent); }
```

⚠️ **Nunca concatenar el alfa al token** (`var(--color-peligro)1a`): produce CSS inválido que el
navegador descarta en silencio — error catalogado en el método §1.4.

| frappe-ui | canónico |
|---|---|
| `bg-surface-red-1`, `-2` | `bg-peligro-tenue` |
| `bg-surface-amber-1`, `-2` | `bg-aviso-tenue` |
| `bg-surface-green-1`, `-2` | `bg-exito-tenue` |
| `border-outline-red-1` | `border-peligro-tenue` |
| `border-outline-amber-1` | `border-aviso-tenue` |

## Rellenos sólidos de estado

`bg-surface-red-5`, `bg-surface-green-6`, `bg-surface-amber-5` son **rellenos**, no fondos tenues:
van con tinta encima. Pasan a `bg-peligro` / `bg-exito` / `bg-aviso`, y **el texto encima debe ser
claro** — recordando que un ámbar de marca es relleno con tinta oscura, nunca texto sobre claro
(método §1.3).

## Iconos

62 clases `lucide-*` → componentes `reicon-vue`. Mapeo verificado en `iconos-mapa.json`: los 62
resuelven a componentes que existen en el paquete.

**Ojo:** la equivalencia **no es mecánica**, pese a que el estilo §4 afirma que el reemplazo lo es
(«mismos nombres en PascalCase»). Medido: **solo 28 de 62 (45%) coinciden**; los otros 34 se
mapearon a mano por semántica. Conviene corregir esa afirmación en el design system.
