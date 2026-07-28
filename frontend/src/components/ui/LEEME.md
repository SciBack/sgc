# Componentes de interfaz

Dos capas, y la distinción importa:

| Carpeta | Qué es | Se edita |
|---|---|---|
| `ui/<nombre>/` (minúsculas) | Traído con `npx shadcn-vue@latest add <nombre>` | **No.** Es upstream |
| `ui/Nombre.vue` (Mayúscula) | Envoltorio de la casa | Sí |

Los de shadcn se dejan intactos para que un `add` futuro los actualice con las
correcciones de accesibilidad de aguas arriba. Todo lo que la casa cambia va en
el envoltorio, que pasa clases por `cn` — `tailwind-merge` resuelve el conflicto
a favor del llamador, así que ganan sin `!important`.

Ver `Boton.vue` como referencia del patrón.

## Los colores no se tocan aquí

Los componentes de shadcn escriben `bg-primary`, `border-input`, `text-muted-foreground`.
Esos tokens están reapuntados a los canónicos de SciBack en el puente de
[`src/style.css`](../../style.css). Por eso salen con la marca sin retocar una sola
clase, y el modo oscuro funciona solo.

**No traduzcas las clases de un componente traído del registro.** Si un color no
sale bien, se corrige el puente, no el componente: cambiarlo lo divorcia de
upstream y rompe el siguiente `add`.

## Iconos: la trampa conocida

`components.json` declara `iconLibrary: lucide` porque **reicon no está entre las
opciones del CLI** (lucide, tabler, hugeicons, phosphor, remixicon). El canon
SciBack exige un solo pack, y es reicon.

Consecuencia práctica: **cualquier `shadcn-vue add` de un componente con iconos
traerá imports de lucide y reinstalará el paquete.** Hay que cambiarlos a
`reicon-vue` a mano y comprobarlo:

```bash
node <ds>/canonico/scripts/verificar-iconos.mjs src
```

Ese verificador mira los imports y las clases CSS reales, no el `package.json`,
así que detecta el pack colado aunque la dependencia esté declarada.

## Cuidado al reejecutar `init`

`shadcn-vue init` **reescribe `src/style.css`**: mete su paleta neutra en oklch,
un bloque `.dark` y —si `components.json` tiene la clave `font`— un `@import` a
Google Fonts en cada `add`. Por eso esa clave está retirada: Inter ya se sirve
local con `@fontsource`, y el import externo añadía una dependencia de red y
filtraba la IP de cada usuario a un tercero.

Si alguien vuelve a correr `init`, hay que revisar el diff de `style.css` entero.

## Lo que NO se adopta, y por qué

Traer todo del registro por seguir la forma sería un error. Dos casos medidos:

**`Cargando`** — el registro tiene `spinner`. Se trajo, se leyó y se descartó:
es un icono de lucide con `animate-spin`, sin texto ni `aria-live`. El nuestro
avisa a los lectores de pantalla y no obliga a un segundo pack de iconos.

**`SelectorBuscador`** — el combobox de shadcn es `Popover` + `Command`, y
`Command` filtra en cliente sin poder desactivarlo. Aquí las opciones llegan ya
filtradas por Frappe, que busca por `name` y por título a la vez; volver a
cribarlas escondería resultados válidos. Sería pérdida de datos silenciosa, no
una diferencia estética. Se queda sobre reka-ui, que es la misma primitiva.

`TituloPagina` y `EnlaceLateral` tampoco tienen equivalente: el lateral del SGC
es cromo de marca propio, no el `sidebar` de shadcn con su proveedor de estado.
