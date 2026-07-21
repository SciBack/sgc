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
        sciback: {
          fondo: 'var(--color-fondo)',
          superficie: 'var(--color-superficie)',
          borde: 'var(--color-borde)',
          tinta: 'var(--color-tinta)',
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
