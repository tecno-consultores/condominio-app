import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const PUBLIC_CRITICAL_ROUTES = ['/login', '/register'];

test.describe('Auditoría WCAG 2.1 AA y Geometría Visual Anti-JSDOM (Hito 5)', () => {
  for (const route of PUBLIC_CRITICAL_ROUTES) {
    test(`La ruta "${route}" cumple con WCAG 2.1 AA sin violaciones en móvil y escritorio`, async ({
      page,
    }) => {
      await page.route('**/api/estructura/unidades', async (r) => {
        await r.fulfill({
          json: [{ id: 1, identificador: 'A-101', estructura_id: 1 }],
        });
      });

      await page.goto(route);
      await page.waitForLoadState('networkidle');

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      expect(results.violations).toEqual([]);
    });
  }
});
