import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { installCondominioApiMock } from './fixtures/condominioApiMock';
import { Actor, BrowseTheWeb } from './screenplay/core';
import { AxeCriticalOrSeriousViolations } from './screenplay/questions';
import {
  EmitBillingAndInspectBreakdown,
  NavigateTo,
  ToggleColorTheme,
  VoteInConsultation,
} from './screenplay/tasks';

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

  test('Diálogo contextual #dialog-contextual-help abre en Top Layer (:modal) con closedby="any" y 0 violaciones WCAG 2.1 AA', async ({
    page,
  }) => {
    await page.goto('/login');
    await expect(page.locator('#btn-contextual-help')).toBeVisible();
    await page.click('#btn-contextual-help');

    const dialog = page.locator('#dialog-contextual-help');
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute('closedby', 'any');
    const isModal = await dialog.evaluate((el) => el.matches(':modal'));
    expect(isModal).toBe(true);
    await dialog.evaluate((el) => Promise.allSettled(el.getAnimations().map((a) => a.finished)));

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    const criticalOrSerious = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious',
    );
    expect(criticalOrSerious).toEqual([]);

    await page.click('#btn-close-help');
    await expect(dialog).toHaveCount(0);
  });

  test('Hito 15: Tokens OKLCH, Modo Oscuro (#btn-theme-toggle), Touch Targets >= 44px y Bottom Sheet cumplen WCAG 2.1 AA', async ({
    page,
  }) => {
    await page.goto('/login');
    const colorSchemeMeta = page.locator('meta[name="color-scheme"]');
    await expect(colorSchemeMeta).toHaveAttribute('content', 'light dark');

    const toggleBtn = page.locator('#btn-theme-toggle');
    await expect(toggleBtn).toBeVisible();
    const toggleBox = await toggleBtn.boundingBox();
    expect(toggleBox).not.toBeNull();
    expect(toggleBox?.width).toBeGreaterThanOrEqual(44);
    expect(toggleBox?.height).toBeGreaterThanOrEqual(44);

    // Activar modo oscuro explícito y auditar WCAG 2.1 AA en /login + Bottom Sheet
    await toggleBtn.click();
    await expect(colorSchemeMeta).toHaveAttribute('content', 'dark');
    const isDarkRoot = await page.evaluate(() =>
      document.documentElement.classList.contains('theme-dark'),
    );
    expect(isDarkRoot).toBe(true);

    const loginDarkAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(
      loginDarkAxe.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious'),
    ).toEqual([]);

    await page.click('#btn-contextual-help');
    const dialog = page.locator('#dialog-contextual-help');
    await expect(dialog).toBeVisible();
    await dialog.evaluate((el) => Promise.allSettled(el.getAnimations().map((a) => a.finished)));

    const viewport = page.viewportSize();
    if (viewport && viewport.width < 640) {
      await expect(async () => {
        const dialogBox = await dialog.boundingBox();
        expect(dialogBox).not.toBeNull();
        expect(dialogBox?.width).toBeGreaterThanOrEqual(viewport.width * 0.95);
        if (dialogBox) {
          expect(Math.abs(dialogBox.y + dialogBox.height - viewport.height)).toBeLessThanOrEqual(4);
        }
      }).toPass({ timeout: 2000 });
    }

    const modalDarkAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(
      modalDarkAxe.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious'),
    ).toEqual([]);

    await page.click('#btn-close-help');
    await expect(dialog).toHaveCount(0);

    // Auditar /register en modo oscuro persistido
    await page.goto('/register');
    await expect(page.locator('#btn-register-submit')).toBeVisible();
    const registerDarkAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(
      registerDarkAxe.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious'),
    ).toEqual([]);
  });
});

async function assertZeroAxeCriticalOrSerious(actor: Actor, path: string): Promise<void> {
  await actor.attemptsTo(NavigateTo.path(path));
  await actor.attemptsTo(ToggleColorTheme.to('light'));
  expect(await actor.asks(AxeCriticalOrSeriousViolations.detected())).toEqual([]);
  await actor.attemptsTo(ToggleColorTheme.to('dark'));
  expect(await actor.asks(AxeCriticalOrSeriousViolations.detected())).toEqual([]);
}

test.describe('Auditoría WCAG 2.1 AA en Vistas Autenticadas Claro/Oscuro (Hito 8)', () => {
  test('1. Contención Fantasma (/espera-aprobacion) cumple WCAG 2.1 AA en claro y oscuro', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: 'FANTASMA' });
    const fantasma = Actor.named('A11yFantasma').whoCan(BrowseTheWeb.using(page));
    await assertZeroAxeCriticalOrSerious(fantasma, '/espera-aprobacion');
  });

  test('2. Vistas Financieras y Desglose Top-Layer cumplen WCAG 2.1 AA en claro y oscuro', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: 'TESORERO' });
    const tesorero = Actor.named('A11yTesorero').whoCan(BrowseTheWeb.using(page));

    for (const path of ['/dashboard', '/finanzas/reportar-pago', '/finanzas/solvencia']) {
      await assertZeroAxeCriticalOrSerious(tesorero, path);
    }

    await tesorero.attemptsTo(EmitBillingAndInspectBreakdown.forDefaultPeriod());
    await tesorero.attemptsTo(ToggleColorTheme.to('light'));
    expect(await tesorero.asks(AxeCriticalOrSeriousViolations.detected())).toEqual([]);
    await tesorero.attemptsTo(ToggleColorTheme.to('dark'));
    expect(await tesorero.asks(AxeCriticalOrSeriousViolations.detected())).toEqual([]);
    await page.locator('#btn-close-desglose').click();
  });

  test('3. Vistas Operativas, Gobernanza (+ VoteReceiptModal), Accesos y Admin cumplen WCAG 2.1 AA en claro y oscuro', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: 'PRESIDENTE' });
    const presidente = Actor.named('A11yPresidente').whoCan(BrowseTheWeb.using(page));

    const routes = [
      '/incidencias',
      '/operaciones/tareas',
      '/accesos/pases',
      '/operaciones/paqueteria',
      '/reservas/areas',
      '/admin/usuarios',
    ];
    for (const path of routes) {
      await assertZeroAxeCriticalOrSerious(presidente, path);
    }

    await presidente.attemptsTo(VoteInConsultation.firstOpenOption());
    await presidente.attemptsTo(ToggleColorTheme.to('light'));
    expect(await presidente.asks(AxeCriticalOrSeriousViolations.detected())).toEqual([]);
    await presidente.attemptsTo(ToggleColorTheme.to('dark'));
    expect(await presidente.asks(AxeCriticalOrSeriousViolations.detected())).toEqual([]);
    await page.locator('#btn-close-vote-receipt').click();
  });
});
