// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { expect, test } from '@playwright/test';
import { installCondominioApiMock } from './fixtures/condominioApiMock';
import { Actor, BrowseTheWeb } from './screenplay/core';
import { NavigateTo, ToggleColorTheme } from './screenplay/tasks';

test.describe('Regresión Visual Multi-Tema y Multi-Viewport (Hito 8)', () => {
  test('1. Snapshot visual de Login en tema claro', async ({ page }) => {
    const actor = Actor.named('VisualLoginLight').whoCan(BrowseTheWeb.using(page));
    await actor.attemptsTo(NavigateTo.path('/login'), ToggleColorTheme.to('light'));
    await expect(page).toHaveScreenshot('login-light.png', {
      fullPage: true,
    });
  });

  test('2. Snapshot visual de Login en tema oscuro (light-dark)', async ({ page }) => {
    const actor = Actor.named('VisualLoginDark').whoCan(BrowseTheWeb.using(page));
    await actor.attemptsTo(NavigateTo.path('/login'), ToggleColorTheme.to('dark'));
    await expect(page).toHaveScreenshot('login-dark.png', {
      fullPage: true,
    });
  });

  test('3. Snapshot visual de Dashboard autenticado en tema claro', async ({ page }) => {
    await installCondominioApiMock(page, { initialProfile: 'PROPIETARIO' });
    const actor = Actor.named('VisualDashLight').whoCan(BrowseTheWeb.using(page));
    await actor.attemptsTo(NavigateTo.path('/dashboard'), ToggleColorTheme.to('light'));
    await expect(page).toHaveScreenshot('dashboard-light.png', {
      fullPage: true,
    });
  });

  test('4. Snapshot visual de Dashboard autenticado en tema oscuro', async ({ page }) => {
    await installCondominioApiMock(page, { initialProfile: 'PROPIETARIO' });
    const actor = Actor.named('VisualDashDark').whoCan(BrowseTheWeb.using(page));
    await actor.attemptsTo(NavigateTo.path('/dashboard'), ToggleColorTheme.to('dark'));
    await expect(page).toHaveScreenshot('dashboard-dark.png', {
      fullPage: true,
    });
  });

  test('5. Snapshot visual de Detalle de Consulta Art. 23 en tema claro', async ({ page }) => {
    await installCondominioApiMock(page, { initialProfile: 'PROPIETARIO' });
    const actor = Actor.named('VisualConsultLight').whoCan(BrowseTheWeb.using(page));
    await actor.attemptsTo(NavigateTo.path('/consultas/1'), ToggleColorTheme.to('light'));
    await expect(page).toHaveScreenshot('consultation-detail-light.png', {
      fullPage: true,
    });
  });
});
