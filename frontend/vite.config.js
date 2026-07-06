import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import frappeui from 'frappe-ui/vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
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
