import frappeUIPreset from 'frappe-ui/tailwind'

/** @type {import('tailwindcss').Config} */
export default {
  presets: [frappeUIPreset],
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/frappe-ui/frappe/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // SciBack DS 2.0: los colores se piden por función. UPeU solo reviste
        // `marca-*`; los neutros y estados permanecen canónicos.
        marca: {
          primaria: {
            50: 'var(--color-marca-primaria-50)',
            100: 'var(--color-marca-primaria-100)',
            200: 'var(--color-marca-primaria-200)',
            300: 'var(--color-marca-primaria-300)',
            400: 'var(--color-marca-primaria-400)',
            500: 'var(--color-marca-primaria-500)',
            600: 'var(--color-marca-primaria-600)',
            700: 'var(--color-marca-primaria-700)',
            800: 'var(--color-marca-primaria-800)',
            900: 'var(--color-marca-primaria-900)',
          },
          secundaria: {
            50: 'var(--color-marca-secundaria-50)',
            100: 'var(--color-marca-secundaria-100)',
            200: 'var(--color-marca-secundaria-200)',
            300: 'var(--color-marca-secundaria-300)',
            400: 'var(--color-marca-secundaria-400)',
            500: 'var(--color-marca-secundaria-500)',
            600: 'var(--color-marca-secundaria-600)',
            700: 'var(--color-marca-secundaria-700)',
            800: 'var(--color-marca-secundaria-800)',
          },
        },
        // Semánticos canónicos, SIN namespace: el estilo SciBack los escribe
        // `bg-superficie`, `text-tinta-tenue`, `border-borde`. Antes vivían bajo
        // `sciback-*` y solo estaban 4 de los 13, así que escribir la clase del
        // canon no generaba NADA y el estilo se perdía en silencio — el error nº2
        // del catálogo del método, que ni `tsc` ni el linter detectan.
        // Se declaran COMPLETOS a propósito: una escala a medias es justo lo que
        // hace que una clase válida no exista.
        fondo: 'var(--color-fondo)',
        superficie: {
          DEFAULT: 'var(--color-superficie)',
          2: 'var(--color-superficie-2)',
          3: 'var(--color-superficie-3)',
        },
        borde: {
          DEFAULT: 'var(--color-borde)',
          fuerte: 'var(--color-borde-fuerte)',
        },
        tinta: {
          DEFAULT: 'var(--color-tinta)',
          suave: 'var(--color-tinta-suave)',
          tenue: 'var(--color-tinta-tenue)',
        },
        info: 'var(--color-info)',
        exito: 'var(--color-exito)',
        aviso: 'var(--color-aviso)',
        peligro: 'var(--color-peligro)',
        rejilla: 'var(--color-rejilla)',
        serie: {
          1: 'var(--color-serie-1)',
          2: 'var(--color-serie-2)',
          3: 'var(--color-serie-3)',
          4: 'var(--color-serie-4)',
          5: 'var(--color-serie-5)',
        },
      },
      fontFamily: {
        // La SPA es una herramienta de trabajo: la misma sans variable en
        // títulos, datos y controles evita el contraste editorial anticuado.
        display: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
}
