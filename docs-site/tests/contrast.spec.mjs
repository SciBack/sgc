import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// El tema se fija ANTES de cargar la página, como lo tendría un usuario: preferencia del sistema
// y la elección guardada que lee el script en línea de Starlight (ThemeProvider) al arrancar.
// Cambiarlo después de cargar competía con ese script y axe llegaba a medir el acento del tema
// claro sobre el fondo del oscuro, un estado que no ve nadie (#78).
for (const theme of ['light', 'dark']) {
  test(`contraste WCAG AA en tema ${theme}`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: theme });
    await page.addInitScript((value) => localStorage.setItem('starlight-theme', value), theme);
    await page.goto('./flujos/documento-controlado/');

    // Si el tema no se aplicó, el test falla por eso y lo dice: no mide una mezcla en silencio.
    await expect(page.locator('html')).toHaveAttribute('data-theme', theme);

    const result = await new AxeBuilder({ page }).withTags(['wcag2aa']).analyze();
    const contrast = result.violations.filter((violation) => violation.id === 'color-contrast');
    expect(contrast, JSON.stringify(contrast, null, 2)).toEqual([]);
  });
}
