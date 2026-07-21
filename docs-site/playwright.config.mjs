import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: /(?:visual|contrast)\.spec\.mjs/,
  fullyParallel: false,
  retries: 0,
  reporter: 'line',
  use: { baseURL: 'http://127.0.0.1:4321/manual/', channel: 'chrome', headless: true },
  webServer: {
    command: 'DOCS_SITE=https://calidad.upeu.edu.pe DOCS_BASE=/manual npm run preview -- --host 127.0.0.1 --port 4321',
    url: 'http://127.0.0.1:4321/manual/',
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
