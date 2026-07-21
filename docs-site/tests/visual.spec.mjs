import { expect, test } from '@playwright/test';

for (const viewport of [{ name: 'desktop', width: 1440, height: 1000 }, { name: 'mobile', width: 390, height: 844 }]) {
  for (const theme of ['light', 'dark']) {
    test(`${viewport.name} ${theme} sin overflow y con navegación`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto('./');
      await page.evaluate((value) => document.documentElement.dataset.theme = value, theme);
      await expect(page).toHaveTitle(/Manual funcional del SGC/);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow).toBeLessThanOrEqual(1);
      await expect(page.getByRole('link', { name: /Preparar las pruebas/i }).first()).toBeVisible();
      if (viewport.name === 'mobile') {
        await page.goto('proposito/');
        await expect(page.getByRole('button', { name: /menu/i })).toBeVisible();
      }
    });
  }
}

test('rol, flujo largo y búsqueda cargan', async ({ page }) => {
  for (const route of ['roles/dpgc/', 'flujos/documento-controlado/', 'checklist-regresion/']) {
    await page.goto(route);
    await expect(page.locator('main h1')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  }
  await page.goto('./');
  await expect(page.getByRole('button', { name: /search|buscar/i })).toBeVisible();
});
