import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test.describe('Hitos 5, 6, 10 y 11 — Accesibilidad WCAG 2.1 AA y Geometría Visual Anti-JSDOM', () => {
  test('Vista /login cumple 0 violaciones WCAG 2.1 AA críticas o serias', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('#login-form')).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    const criticalOrSerious = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious',
    );
    expect(criticalOrSerious).toEqual([]);
  });

  test('Vista /register cumple 0 violaciones WCAG 2.1 AA y el botón submit es visible en viewport', async ({
    page,
  }) => {
    await page.goto('/register');
    const submitBtn = page.locator('#btn-register-submit');
    await expect(submitBtn).toBeVisible();

    const box = await submitBtn.boundingBox();
    expect(box).not.toBeNull();
    expect(box?.height).toBeGreaterThanOrEqual(44);

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    const criticalOrSerious = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious',
    );
    expect(criticalOrSerious).toEqual([]);
  });

  test('Rutas protegidas de Gobernanza Digital (/consultas), Accesos QR (/accesos/pases) y Reservas (/reservas/areas) redirigen a /login preservando WCAG 2.1 AA', async ({
    page,
  }) => {
    await page.goto('/consultas');
    await expect(page.locator('#login-form')).toBeVisible();

    await page.goto('/accesos/pases');
    await expect(page.locator('#login-form')).toBeVisible();

    await page.goto('/reservas/areas');
    await expect(page.locator('#login-form')).toBeVisible();

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    const criticalOrSerious = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious',
    );
    expect(criticalOrSerious).toEqual([]);
  });
});
