import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import frappeui from 'frappe-ui/vite'

/* Tailwind 4 cambia una regla que Tailwind 3 no tenia: un bloque `<style>` de un
 * SFC se compila AISLADO y no ve el tema, asi que cualquier `theme(...)` dentro
 * falla. frappe-ui se distribuye como fuente sin compilar y sus SFC usan
 * `theme('colors.gray.900')`, de modo que el build entero se cae por un editor de
 * texto que este producto ni siquiera renderiza.
 *
 * `@reference` es el mecanismo que TW4 da para eso: carga el tema en modo
 * referencia (no emite CSS) y deja que `theme()` resuelva. Se inyecta solo en el
 * CSS que viene de frappe-ui; el nuestro ya lo tiene por el import normal.
 *
 * Se descarto importar en profundidad (`frappe-ui/src/...`) para esquivar el
 * barrel: el campo `exports` del paquete no expone esas rutas. */
const referenciarTemaEnFrappeUI = () => ({
  name: 'sgc:referencia-tema-frappe-ui',
  enforce: 'pre',
  transform(codigo, id) {
    if (!id.includes('frappe-ui') || !id.includes('type=style')) return null
    if (codigo.includes('@reference')) return null
    return { code: `@reference "${path.resolve(__dirname, 'src/style.css')}";\n${codigo}`, map: null }
  },
})

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    referenciarTemaEnFrappeUI(),
    frappeui({
      frontendRoute: '/sgc',
      frappeProxy: true,
      jinjaBootData: true,
      buildConfig: {
        indexHtmlPath: '../sgc/www/sgc.html',
        emptyOutDir: true,
        sourcemap: true,
      },
    }),
    vue(),
    // Tailwind 4 entra por plugin de Vite, no por PostCSS (guia oficial de shadcn-vue).
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  optimizeDeps: {
    // frappe-ui ships unbuilt source with `~icons/lucide/*` virtual imports
    // that esbuild's prebundler cannot resolve; the frappeui plugin resolves
    // them at request time instead.
    exclude: ['frappe-ui'],
    include: [
      'feather-icons',
      'tippy.js',
      'engine.io-client',
      'socket.io-client',
      'debug',
    ],
  },
})
