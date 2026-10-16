import { expect, test } from '@playwright/test';

for (const viewport of [{ name: 'desktop', width: 1440, height: 1000 }, { name: 'mobile', width: 390, height: 844 }]) {
  for (const theme of ['light', 'dark']) {
    test(`${viewport.name} ${theme} sin overflow y con navegación`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto('./');
      await page.evaluate((value) => document.documentElement.dataset.theme = value, theme);
      await expect(page).toHaveTitle(/Manual del SGC/);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);
      await expect(page.getByRole('link', { name: /Primeros pasos/i }).first()).toBeVisible();
      if (viewport.name === 'mobile') {
        await page.goto('primeros-pasos/');
        await expect(page.getByRole('button', { name: /menu/i })).toBeVisible();
      }
    });
  }
}

// Los manuales por área llevan tablas de estados de 4 y 5 columnas: lo primero que se desborda en
// un teléfono. Se comprueba cada uno en la anchura de móvil, no solo la portada.
const MANUALES_POR_AREA = [
  'procesos/', 'documentos/', 'indicadores/', 'acreditacion/', 'mejora-continua/',
  'auditoria/', 'riesgos/', 'direccion/', 'configuracion/autogestion/', 'tutoriales/publicar-ficha/',
];

test('manuales por área sin desbordar en móvil', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const route of MANUALES_POR_AREA) {
    await page.goto(route);
    await expect(page.locator('main h1'), route).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, route).toBeLessThanOrEqual(1);
  }
});

test('perfiles, manual largo y búsqueda cargan', async ({ page }) => {
  for (const route of ['perfiles/', 'procesos/', 'acreditacion/autoevaluacion/']) {
    await page.goto(route);
    await expect(page.locator('main h1')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  }
  await page.goto('./');
  await expect(page.getByRole('button', { name: /search|buscar/i })).toBeVisible();
});
