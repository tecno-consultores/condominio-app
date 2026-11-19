// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { expect, test } from '@playwright/test';
import { installCondominioApiMock } from './fixtures/condominioApiMock';
import { Actor, BrowseTheWeb } from './screenplay/core';
import {
  CurrentPathname,
  ElementAttribute,
  IsElementVisible,
  TextOfElement,
  ViewportGeometryAudit,
  VisibleHeading,
} from './screenplay/questions';
import {
  ActivateFirstPendingResident,
  ApprovePendingPayment,
  AttemptConsultationVote,
  Authenticate,
  CloseModal,
  CompleteFirstDailyTask,
  CopySecretToken,
  EmitBillingAndInspectBreakdown,
  ExecuteMonthlyClosing,
  IssueAndVerifySolvency,
  IssueVisitorQrPass,
  Logout,
  LogoutFromMobileTopBar,
  NavigateTo,
  NavigateViaMobileDrawer,
  OpenMobileNavDrawer,
  RegisterNewResident,
  ReportAndSupportIncident,
  ReportPayment,
  RequestAmenityReservation,
  RequestAndCancelAmenity,
  ResizeViewport,
  ReturnHomeFromNotFound,
  VerifyQrPassAtGatehouse,
  VoteInConsultation,
} from './screenplay/tasks';

async function assertNoOcclusionOrOverflow(
  actor: Actor,
  expectShellFooter: boolean,
): Promise<void> {
  const audit = await actor.asks(ViewportGeometryAudit.snapshot());
  expect(audit.hasHorizontalOverflow).toBe(false);
  expect(audit.footerOccluded).toBe(false);
  expect(audit.occludedControls).toEqual([]);
  if (expectShellFooter) {
    expect(audit.footerPosition).not.toBe('fixed');
    expect(audit.footerPosition).not.toBe('sticky');
    expect(audit.footerPosition).not.toBeNull();
  }
}

test.describe('Flujos E2E Autenticados y Geometría Anti-JSDOM (Hito 8)', () => {
  test('1. Contención de Usuario Fantasma tras registro y asignación por Presidencia', async ({
    page,
  }) => {
    const mockState = await installCondominioApiMock(page);
    const residente = Actor.named('Residente').whoCan(BrowseTheWeb.using(page));

    await residente.attemptsTo(RegisterNewResident.withEmail('valeria.nueva@condominio.test'));
    expect(await residente.asks(CurrentPathname.value())).toBe('/espera-aprobacion');
    expect(mockState.capturedIdempotencyKeys.length).toBeGreaterThanOrEqual(1);
    await assertNoOcclusionOrOverflow(residente, false);

    // Intento de saltar al dashboard es contenido por el guard RBAC hacia /espera-aprobacion
    await residente.attemptsTo(NavigateTo.path('/dashboard'));
    expect(await residente.asks(CurrentPathname.value())).toBe('/espera-aprobacion');

    await residente.attemptsTo(Logout.viaAccessibleButton('Cerrar sesión'));

    const presidente = Actor.named('Presidente').whoCan(BrowseTheWeb.using(page));
    await presidente.attemptsTo(
      Authenticate.withCredentials('presidente@condominio.test', 'Presidente123!'),
      ActivateFirstPendingResident.now(),
    );
    expect(await presidente.asks(TextOfElement.matching('#ghost-success-banner'))).toContain(
      'activado',
    );
    await assertNoOcclusionOrOverflow(presidente, true);
  });

  test('2. Ciclo Financiero Trimodal (Hitos 6 y 10): Reporte Idempotente, Facturación, Solvencia y Candado', async ({
    page,
  }) => {
    const mockState = await installCondominioApiMock(page, { initialProfile: 'PROPIETARIO' });
    const propietario = Actor.named('Propietario').whoCan(BrowseTheWeb.using(page));

    await propietario.attemptsTo(
      NavigateTo.path('/dashboard'),
      ReportPayment.amountWithReference('1825.00', 'PM-99887766'),
    );
    expect(await propietario.asks(CurrentPathname.value())).toBe('/dashboard');
    expect(mockState.capturedIdempotencyKeys.length).toBeGreaterThanOrEqual(1);
    await assertNoOcclusionOrOverflow(propietario, true);

    await installCondominioApiMock(page, { initialProfile: 'TESORERO' });
    const tesorero = Actor.named('Tesorero').whoCan(BrowseTheWeb.using(page));
    await tesorero.attemptsTo(
      ApprovePendingPayment.first(),
      EmitBillingAndInspectBreakdown.forDefaultPeriod(),
    );
    expect(await tesorero.asks(IsElementVisible.matching('#modal-recibo-desglose'))).toBe(true);
    await tesorero.attemptsTo(CloseModal.byButton('#btn-close-desglose', '#modal-recibo-desglose'));

    await tesorero.attemptsTo(IssueAndVerifySolvency.forActiveUnit());
    expect(await tesorero.asks(TextOfElement.matching('#qr-solvencia-badge'))).toContain('SOLV-');
    await tesorero.attemptsTo(CopySecretToken.viaButton('#btn-copy-solvency-token'));
    expect(
      await tesorero.asks(ElementAttribute.of('#btn-copy-solvency-token', 'data-copied')),
    ).toBe('');
    await tesorero.attemptsTo(ExecuteMonthlyClosing.now());
    expect(await tesorero.asks(TextOfElement.matching('.banner--success'))).toContain('Candado');
    await assertNoOcclusionOrOverflow(tesorero, true);

    // Propietario intentando acceder a /admin/usuarios es redirigido por RBAC hacia /dashboard
    await installCondominioApiMock(page, { initialProfile: 'PROPIETARIO' });
    const rbacActor = Actor.named('PropietarioRBAC').whoCan(BrowseTheWeb.using(page));
    await rbacActor.attemptsTo(NavigateTo.path('/admin/usuarios'));
    expect(await rbacActor.asks(CurrentPathname.value())).toBe('/dashboard');
  });

  test('3. Embudo Operativo y Gobierno (Hitos 7 y 11): Incidencias, Tareas y Votación HMAC', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: 'CONSERJE' });
    const conserje = Actor.named('Conserje').whoCan(BrowseTheWeb.using(page));

    await conserje.attemptsTo(
      ReportAndSupportIncident.withDescription('Filtracion severa en cuarto hidroneumatico'),
      CompleteFirstDailyTask.now(),
    );
    expect(await conserje.asks(TextOfElement.matching('.banner--success'))).toContain('completada');
    await assertNoOcclusionOrOverflow(conserje, true);

    await installCondominioApiMock(page, { initialProfile: 'PROPIETARIO' });
    const votante = Actor.named('Copropietario').whoCan(BrowseTheWeb.using(page));
    await votante.attemptsTo(VoteInConsultation.firstOpenOption());
    expect(await votante.asks(IsElementVisible.matching('#modal-vote-receipt'))).toBe(true);
    expect(await votante.asks(TextOfElement.matching('#receipt-firma-hmac'))).toContain('hmac_');
    await votante.attemptsTo(CopySecretToken.viaButton('#btn-copy-vote-hmac'));
    expect(await votante.asks(ElementAttribute.of('#btn-copy-vote-hmac', 'data-copied'))).toBe('');
    await votante.attemptsTo(CloseModal.byButton('#btn-close-vote-receipt', '#modal-vote-receipt'));
    await assertNoOcclusionOrOverflow(votante, true);
  });

  test('4. Control de Accesos Anti-Replay, Reservas Estrictas y Cancelación (Hitos 12, 13 y 17.4)', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: 'PROPIETARIO' });
    const actor = Actor.named('ResidenteAccesos').whoCan(BrowseTheWeb.using(page));

    await actor.attemptsTo(IssueVisitorQrPass.forVisitor('Elena Tecnica', 'V-18222333'));
    const tokenText = await actor.asks(TextOfElement.matching('code.token-value'));
    expect(tokenText).toContain('hmac_');
    await assertNoOcclusionOrOverflow(actor, true);

    // Primer escaneo válido y segundo escaneo bloqueado (Anti-Replay)
    await installCondominioApiMock(page, { initialProfile: 'CONSERJE' });
    const conserje = Actor.named('Garita').whoCan(BrowseTheWeb.using(page));
    await conserje.attemptsTo(
      VerifyQrPassAtGatehouse.withToken('qr-seed-token-0001.hmac_valid_sig'),
    );
    expect(await conserje.asks(IsElementVisible.matching('#qr-scan-success-card'))).toBe(true);
    await conserje.attemptsTo(
      VerifyQrPassAtGatehouse.withToken('qr-seed-token-0001.hmac_valid_sig'),
    );
    expect(await conserje.asks(IsElementVisible.matching('#qr-scan-error-alert'))).toBe(true);

    // Reserva y cancelación Hito 17.4
    await conserje.attemptsTo(RequestAndCancelAmenity.withReason('Asamblea de piso 2'));
    expect(
      await conserje.asks(TextOfElement.matching('#reservation-card-1, .reservation-card')),
    ).toContain('CANCELADA');
    await assertNoOcclusionOrOverflow(conserje, true);

    // Bloqueo por morosidad (403) en reserva estricta
    await installCondominioApiMock(page, {
      initialProfile: 'PROPIETARIO',
      strictSolvencyBlock: true,
    });
    const moroso = Actor.named('Moroso').whoCan(BrowseTheWeb.using(page));
    await moroso.attemptsTo(RequestAmenityReservation.withReason('Celebracion familiar bloqueada'));
    expect(await moroso.asks(TextOfElement.matching('.alert--error, [role="alert"]'))).toContain(
      'solvente',
    );
    expect(await moroso.asks(VisibleHeading.text())).toContain('Reserva');
  });

  test('5. Hito 22: Cajón móvil < 768px, logout móvil, ruta 404 y resiliencia de Dashboard', async ({
    page,
  }) => {
    await installCondominioApiMock(page, {
      initialProfile: 'PROPIETARIO',
      omitDailyRate: true,
      omitResumen: true,
    });
    const movil = Actor.named('ResidenteMovil').whoCan(BrowseTheWeb.using(page));

    await movil.attemptsTo(ResizeViewport.to(375, 667), NavigateTo.path('/dashboard'));
    expect(await movil.asks(TextOfElement.matching('#daily-rate-badge'))).toContain(
      'Tasa BCV pendiente hoy',
    );
    expect(await movil.asks(TextOfElement.matching('#deuda-card'))).not.toContain(
      'Solvente / Al día',
    );
    await assertNoOcclusionOrOverflow(movil, true);

    // Drawer móvil en Top Layer y acceso a ruta secundaria
    await movil.attemptsTo(OpenMobileNavDrawer.now());
    expect(await movil.asks(IsElementVisible.matching('#mobile-nav-drawer'))).toBe(true);
    await movil.attemptsTo(NavigateViaMobileDrawer.toLabel('Cartas Consulta', '**/consultas'));
    expect(await movil.asks(CurrentPathname.value())).toBe('/consultas');

    // Ruta desconocida -> #not-found-card
    await movil.attemptsTo(NavigateTo.path('/ruta-inexistente-404'));
    expect(await movil.asks(IsElementVisible.matching('#not-found-card'))).toBe(true);
    await movil.attemptsTo(ReturnHomeFromNotFound.now());
    expect(await movil.asks(CurrentPathname.value())).toBe('/dashboard');

    // Botón móvil de salida visible en barra superior
    await movil.attemptsTo(LogoutFromMobileTopBar.now());
    expect(await movil.asks(CurrentPathname.value())).toBe('/login');
  });

  test('6. Hito 23: Contención RBAC 403 en votación de Inquilino y error 404 en Tasa BCV', async ({
    page,
  }) => {
    await installCondominioApiMock(page, { initialProfile: 'INQUILINO' });
    const inquilino = Actor.named('InquilinoRBAC').whoCan(BrowseTheWeb.using(page));

    await inquilino.attemptsTo(AttemptConsultationVote.onConsultation(1));
    expect(await inquilino.asks(TextOfElement.matching('.banner--error'))).toContain('propietario');

    await installCondominioApiMock(page, {
      initialProfile: 'PROPIETARIO',
      omitDailyRate: true,
    });
    const residente = Actor.named('ResidenteSinTasa').whoCan(BrowseTheWeb.using(page));
    await residente.attemptsTo(NavigateTo.path('/dashboard'));
    expect(await residente.asks(TextOfElement.matching('#daily-rate-badge'))).toContain(
      'Tasa BCV pendiente hoy',
    );
  });
});
