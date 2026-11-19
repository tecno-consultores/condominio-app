// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { expect, test } from '@playwright/test';
import { installCondominioApiMock, type ProfileKey } from './fixtures/condominioApiMock';
import { Actor, BrowseTheWeb } from './screenplay/core';
import {
  AxeCriticalOrSeriousViolations,
  CurrentColorScheme,
  CurrentPathname,
  CurrentViewportSize,
  ElementAttribute,
  ElementBoundingBox,
  ElementCount,
  HorizontalOverflow,
  IsDialogInTopLayer,
  IsElementVisible,
} from './screenplay/questions';
import {
  ClickThemeToggleButton,
  CloseContextualHelp,
  CloseModal,
  EmitBillingAndInspectBreakdown,
  NavigateTo,
  OpenContextualHelp,
  OpenMobileNavDrawer,
  ResizeViewport,
  ToggleColorTheme,
  VoteInConsultation,
} from './screenplay/tasks';

async function assertThemeAxeAndOverflow(actor: Actor, label: string): Promise<void> {
  expect(await actor.asks(AxeCriticalOrSeriousViolations.detected()), label).toEqual([]);
  const overflow = await actor.asks(HorizontalOverflow.status());
  expect(
    overflow.hasOverflow,
    `${label} overflow: ${overflow.scrollWidth} > ${overflow.innerWidth}`,
  ).toBe(false);
}

async function assertViewA11yAndOverflow(actor: Actor, path: string): Promise<void> {
  await actor.attemptsTo(NavigateTo.path(path));
  for (const theme of ['light', 'dark'] as const) {
    await actor.attemptsTo(ToggleColorTheme.to(theme));
    await assertThemeAxeAndOverflow(actor, `${path} (${theme})`);
  }
}

async function assertRoleRoutesAccessible(actor: Actor, routes: readonly string[]): Promise<void> {
  for (const path of routes) {
    await assertViewA11yAndOverflow(actor, path);
  }
}

async function assertOpenModalLightAndDark(actor: Actor, label: string): Promise<void> {
  await actor.attemptsTo(ToggleColorTheme.to('light'));
  await assertThemeAxeAndOverflow(actor, `${label} (light)`);
  await actor.attemptsTo(ToggleColorTheme.to('dark'));
  await assertThemeAxeAndOverflow(actor, `${label} (dark)`);
}

test.describe('Hitos 5, 6, 10, 11 y 15 — Accesibilidad WCAG 2.1 AA, Best-Practice y Geometría Anti-JSDOM', () => {
  test('Vistas públicas /login y /ruta-inexistente-qa (404) cumplen WCAG 2.1 AA, best-practice y cero overflow en claro/oscuro', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: null });
    const anon = Actor.named('A11yPublic').whoCan(BrowseTheWeb.using(page));

    await anon.attemptsTo(NavigateTo.path('/login'));
    expect(await anon.asks(IsElementVisible.matching('#login-form'))).toBe(true);
    await assertViewA11yAndOverflow(anon, '/login');
    await assertViewA11yAndOverflow(anon, '/ruta-inexistente-qa');
  });

  test('Vista /register cumple WCAG 2.1 AA, best-practice, cero overflow y botón submit >= 44px', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: null });
    const anon = Actor.named('A11yRegister').whoCan(BrowseTheWeb.using(page));

    await anon.attemptsTo(NavigateTo.path('/register'));
    expect(await anon.asks(IsElementVisible.matching('#btn-register-submit'))).toBe(true);

    const box = await anon.asks(ElementBoundingBox.of('#btn-register-submit'));
    expect(box).not.toBeNull();
    expect(box?.height).toBeGreaterThanOrEqual(44);

    await assertViewA11yAndOverflow(anon, '/register');
  });

  test('Rutas protegidas (/consultas, /accesos/pases, /reservas/areas) redirigen a /login preservando WCAG 2.1 AA y best-practice', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: null });
    const anon = Actor.named('A11yRedirect').whoCan(BrowseTheWeb.using(page));

    for (const protectedPath of ['/consultas', '/accesos/pases', '/reservas/areas']) {
      await anon.attemptsTo(NavigateTo.path(protectedPath));
      expect(await anon.asks(CurrentPathname.value())).toBe('/login');
      expect(await anon.asks(IsElementVisible.matching('#login-form'))).toBe(true);
    }

    await assertThemeAxeAndOverflow(anon, 'protected-redirect-login');
  });

  test('Diálogo contextual #dialog-contextual-help abre en Top Layer (:modal) con closedby="any" y 0 violaciones', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: null });
    const anon = Actor.named('A11yHelpDialog').whoCan(BrowseTheWeb.using(page));

    await anon.attemptsTo(NavigateTo.path('/login'));
    expect(await anon.asks(IsElementVisible.matching('#btn-contextual-help'))).toBe(true);

    await anon.attemptsTo(OpenContextualHelp.now());
    expect(await anon.asks(IsElementVisible.matching('#dialog-contextual-help'))).toBe(true);
    expect(await anon.asks(ElementAttribute.of('#dialog-contextual-help', 'closedby'))).toBe('any');
    expect(await anon.asks(IsDialogInTopLayer.matching('#dialog-contextual-help'))).toBe(true);
    await assertThemeAxeAndOverflow(anon, 'dialog-contextual-help');

    await anon.attemptsTo(CloseContextualHelp.now());
    expect(await anon.asks(ElementCount.matching('#dialog-contextual-help'))).toBe(0);
  });

  test('Hito 15: Tokens OKLCH, Modo Oscuro (#btn-theme-toggle), Touch Targets >= 44px y Bottom Sheet cumplen WCAG 2.1 AA y best-practice', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: null });
    const actor = Actor.named('A11yThemeToggle').whoCan(BrowseTheWeb.using(page));

    await actor.attemptsTo(NavigateTo.path('/login'));
    expect(await actor.asks(ElementAttribute.of('meta[name="color-scheme"]', 'content'))).toBe(
      'light dark',
    );
    expect(await actor.asks(IsElementVisible.matching('#btn-theme-toggle'))).toBe(true);

    const toggleBox = await actor.asks(ElementBoundingBox.of('#btn-theme-toggle'));
    expect(toggleBox).not.toBeNull();
    expect(toggleBox?.width).toBeGreaterThanOrEqual(44);
    expect(toggleBox?.height).toBeGreaterThanOrEqual(44);

    await actor.attemptsTo(ClickThemeToggleButton.now());
    expect(await actor.asks(ElementAttribute.of('meta[name="color-scheme"]', 'content'))).toBe(
      'dark',
    );
    expect(await actor.asks(CurrentColorScheme.mode())).toBe('dark');
    await assertThemeAxeAndOverflow(actor, '/login (dark-toggle)');

    await actor.attemptsTo(OpenContextualHelp.now());
    const viewport = await actor.asks(CurrentViewportSize.dimensions());
    if (viewport && viewport.width < 640) {
      await expect(async () => {
        const dialogBox = await actor.asks(ElementBoundingBox.of('#dialog-contextual-help'));
        expect(dialogBox).not.toBeNull();
        expect(dialogBox?.width).toBeGreaterThanOrEqual(viewport.width * 0.95);
        if (dialogBox) {
          expect(Math.abs(dialogBox.y + dialogBox.height - viewport.height)).toBeLessThanOrEqual(4);
        }
      }).toPass({ timeout: 2000 });
    }

    await assertThemeAxeAndOverflow(actor, 'dialog-contextual-help (dark)');
    await actor.attemptsTo(CloseContextualHelp.now());
    expect(await actor.asks(ElementCount.matching('#dialog-contextual-help'))).toBe(0);

    await actor.attemptsTo(NavigateTo.path('/register'));
    expect(await actor.asks(IsElementVisible.matching('#btn-register-submit'))).toBe(true);
    await assertThemeAxeAndOverflow(actor, '/register (dark-persisted)');
  });
});

test.describe('Auditoría Integral 23/23 Vistas WCAG 2.1 AA + Best-Practice Claro/Oscuro (Hitos 8 y 23)', () => {
  test('1. Contención Fantasma (/espera-aprobacion) cumple WCAG 2.1 AA, best-practice y cero overflow en claro/oscuro', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: 'FANTASMA' });
    const fantasma = Actor.named('A11yFantasma').whoCan(BrowseTheWeb.using(page));
    await assertViewA11yAndOverflow(fantasma, '/espera-aprobacion');
  });

  test('2. Vistas de Tesorería y Finanzas (6 rutas + Desglose Top-Layer) cumplen WCAG 2.1 AA y best-practice', async ({
    page,
  }) => {
    test.setTimeout(60_000);
    await installCondominioApiMock(page, { initialProfile: 'TESORERO' });
    const tesorero = Actor.named('A11yTesorero').whoCan(BrowseTheWeb.using(page));

    await assertRoleRoutesAccessible(tesorero, [
      '/dashboard',
      '/finanzas/reportar-pago',
      '/tesoreria/pagos',
      '/tesoreria/cierre',
      '/tesoreria/facturacion',
      '/finanzas/solvencia',
    ]);

    await tesorero.attemptsTo(EmitBillingAndInspectBreakdown.forDefaultPeriod());
    await assertOpenModalLightAndDark(tesorero, '#modal-recibo-desglose');
    await tesorero.attemptsTo(CloseModal.byButton('#btn-close-desglose', '#modal-recibo-desglose'));
  });

  test('3. Vistas de Secretaría, Vocería y Conserjería (7 rutas) cumplen WCAG 2.1 AA y best-practice', async ({
    page,
  }) => {
    test.setTimeout(60_000);
    const roleGroups: ReadonlyArray<{ role: ProfileKey; routes: readonly string[] }> = [
      { role: 'SECRETARIO', routes: ['/secretaria/bitacora', '/consultas', '/consultas/1'] },
      { role: 'VOCERO', routes: ['/voceros/galeria'] },
      {
        role: 'CONSERJE',
        routes: ['/operaciones/tareas', '/operaciones/garita-qr', '/operaciones/paqueteria'],
      },
    ];

    for (const group of roleGroups) {
      await installCondominioApiMock(page, { initialProfile: group.role });
      const actor = Actor.named(`A11y-${group.role}`).whoCan(BrowseTheWeb.using(page));
      await assertRoleRoutesAccessible(actor, group.routes);
    }
  });

  test('4. Vistas Comunitarias, Accesos y Administración (6 rutas + VoteReceiptModal) cumplen WCAG 2.1 AA y best-practice', async ({
    page,
  }) => {
    test.setTimeout(60_000);
    await installCondominioApiMock(page, { initialProfile: 'PRESIDENTE' });
    const presidente = Actor.named('A11yPresidente').whoCan(BrowseTheWeb.using(page));

    await assertRoleRoutesAccessible(presidente, [
      '/incidencias',
      '/accesos/pases',
      '/reservas/areas',
      '/admin/estructura',
      '/admin/usuarios',
      '/admin/junta',
    ]);

    await presidente.attemptsTo(VoteInConsultation.firstOpenOption());
    await assertOpenModalLightAndDark(presidente, '#modal-vote-receipt');
    await presidente.attemptsTo(
      CloseModal.byButton('#btn-close-vote-receipt', '#modal-vote-receipt'),
    );
  });

  test('5. Hito 22: Cajón Móvil (#mobile-nav-drawer) cumple WCAG 2.1 AA y best-practice en claro y oscuro', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: 'PROPIETARIO' });
    const mobileActor = Actor.named('A11yMovil').whoCan(BrowseTheWeb.using(page));

    await mobileActor.attemptsTo(
      ResizeViewport.to(375, 667),
      NavigateTo.path('/dashboard'),
      OpenMobileNavDrawer.now(),
    );
    expect(await mobileActor.asks(IsElementVisible.matching('#mobile-nav-drawer'))).toBe(true);
    await assertOpenModalLightAndDark(mobileActor, '#mobile-nav-drawer');
  });
});
