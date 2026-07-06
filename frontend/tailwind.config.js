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
        // Marca institucional UPeU — accesorios (logo, hero, píldoras de
        // estado). El resto de la UI usa los tokens semánticos de frappe-ui
        // (text-ink-*, bg-surface-*) para heredar dark mode gratis.
        upeu: {
          navy: '#003865',
          'navy-700': '#01477e',
          'navy-050': '#eaf1f7',
          gold: '#f7a800',
        },
      },
    },
  },
}
