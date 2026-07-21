import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

for (const theme of ['light', 'dark']) {
  test(`contraste WCAG AA en tema ${theme}`, async ({ page }) => {
    await page.goto('./flujos/documento-controlado/');
    await page.evaluate((value) => document.documentElement.dataset.theme = value, theme);
    const result = await new AxeBuilder({ page }).withTags(['wcag2aa']).analyze();
    const contrast = result.violations.filter((violation) => violation.id === 'color-contrast');
    expect(contrast, JSON.stringify(contrast, null, 2)).toEqual([]);
  });
}
