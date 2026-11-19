// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { expect, test } from '@playwright/test';
import { installCondominioApiMock } from './fixtures/condominioApiMock';
import { Actor, BrowseTheWeb } from './screenplay/core';
import { VisualSnapshotReady } from './screenplay/questions';
import { NavigateTo, ToggleColorTheme } from './screenplay/tasks';

test.describe('Regresión Visual Multi-Tema y Multi-Viewport (Hitos 8 y 23)', () => {
  test('1. Snapshot visual de Login en tema claro', async ({ page }) => {
    await installCondominioApiMock(page, { initialProfile: null });
    const actor = Actor.named('VisualLoginLight').whoCan(BrowseTheWeb.using(page));
    await actor.attemptsTo(NavigateTo.path('/login'), ToggleColorTheme.to('light'));
    expect(await actor.asks(VisualSnapshotReady.verified())).toBe(true);
    await expect(page).toHaveScreenshot('login-light.png', {
      fullPage: true,
    });
  });

  test('2. Snapshot visual de Login en tema oscuro (light-dark)', async ({ page }) => {
    await installCondominioApiMock(page, { initialProfile: null });
    const actor = Actor.named('VisualLoginDark').whoCan(BrowseTheWeb.using(page));
    await actor.attemptsTo(NavigateTo.path('/login'), ToggleColorTheme.to('dark'));
    expect(await actor.asks(VisualSnapshotReady.verified())).toBe(true);
    await expect(page).toHaveScreenshot('login-dark.png', {
      fullPage: true,
    });
  });

  test('3. Snapshot visual de Dashboard autenticado en tema claro', async ({ page }) => {
    await installCondominioApiMock(page, { initialProfile: 'PROPIETARIO' });
    const actor = Actor.named('VisualDashLight').whoCan(BrowseTheWeb.using(page));
    await actor.attemptsTo(NavigateTo.path('/dashboard'), ToggleColorTheme.to('light'));
    expect(await actor.asks(VisualSnapshotReady.verified())).toBe(true);
    await expect(page).toHaveScreenshot('dashboard-light.png', {
      fullPage: true,
    });
  });

  test('4. Snapshot visual de Dashboard autenticado en tema oscuro', async ({ page }) => {
    await installCondominioApiMock(page, { initialProfile: 'PROPIETARIO' });
    const actor = Actor.named('VisualDashDark').whoCan(BrowseTheWeb.using(page));
    await actor.attemptsTo(NavigateTo.path('/dashboard'), ToggleColorTheme.to('dark'));
    expect(await actor.asks(VisualSnapshotReady.verified())).toBe(true);
    await expect(page).toHaveScreenshot('dashboard-dark.png', {
      fullPage: true,
    });
  });

  test('5. Snapshot visual de Detalle de Consulta Art. 23 en tema claro', async ({ page }) => {
    await installCondominioApiMock(page, { initialProfile: 'PROPIETARIO' });
    const actor = Actor.named('VisualConsultLight').whoCan(BrowseTheWeb.using(page));
    await actor.attemptsTo(NavigateTo.path('/consultas/1'), ToggleColorTheme.to('light'));
    expect(await actor.asks(VisualSnapshotReady.verified())).toBe(true);
    await expect(page).toHaveScreenshot('consultation-detail-light.png', {
      fullPage: true,
    });
  });

  test('6. Snapshot visual de Detalle de Consulta Art. 23 en tema oscuro', async ({ page }) => {
    await installCondominioApiMock(page, { initialProfile: 'PROPIETARIO' });
    const actor = Actor.named('VisualConsultDark').whoCan(BrowseTheWeb.using(page));
    await actor.attemptsTo(NavigateTo.path('/consultas/1'), ToggleColorTheme.to('dark'));
    expect(await actor.asks(VisualSnapshotReady.verified())).toBe(true);
    await expect(page).toHaveScreenshot('consultation-detail-dark.png', {
      fullPage: true,
    });
  });
});
