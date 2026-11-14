// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { waitForDialogSettled, type Actor, type Task } from './core';

export class NavigateTo implements Task {
  readonly description: string;

  private constructor(private readonly path: string) {
    this.description = `navegar hacia ${path}`;
  }

  static path(path: string): NavigateTo {
    return new NavigateTo(path);
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto(this.path, { waitUntil: 'domcontentloaded' });
    await page.locator('h1').first().waitFor({ state: 'visible' });
  }
}

export class Authenticate implements Task {
  readonly description: string;

  private constructor(
    private readonly correo: string,
    private readonly password: string,
  ) {
    this.description = `iniciar sesión con ${correo}`;
  }

  static withCredentials(correo: string, password: string): Authenticate {
    return new Authenticate(correo, password);
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/login', { waitUntil: 'domcontentloaded' });
    await page.getByLabel('Correo electrónico').fill(this.correo);
    await page.locator('#login-password').fill(this.password);
    await page.getByRole('button', { name: 'Iniciar sesión' }).click();
    await page.waitForURL(/\/(dashboard|espera-aprobacion|finanzas|tesoreria|admin|consultas)/);
    await page.locator('h1').first().waitFor({ state: 'visible' });
  }
}

export class RegisterNewResident implements Task {
  readonly description = 'registrar nuevo residente hacia estado fantasma';

  private constructor(private readonly correo: string) {}

  static withEmail(correo: string): RegisterNewResident {
    return new RegisterNewResident(correo);
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/register', { waitUntil: 'domcontentloaded' });
    await page.locator('#reg-nombre').fill('Valeria Nuevo Residente');
    await page.locator('#reg-cedula').fill('V-24555666');
    await page.locator('#reg-correo').fill(this.correo);
    await page.locator('#reg-telefono').fill('0414-5559988');
    await page.locator('#reg-password').fill('ClaveSegura2026!');
    await page.locator('#btn-register-submit').click();
    await page.waitForURL('**/espera-aprobacion');
    await page.locator('h1').first().waitFor({ state: 'visible' });
  }
}

export class ToggleColorTheme implements Task {
  readonly description: string;

  private constructor(private readonly target: 'light' | 'dark') {
    this.description = `activar tema visual ${target}`;
  }

  static to(target: 'light' | 'dark'): ToggleColorTheme {
    return new ToggleColorTheme(target);
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.evaluate((theme) => {
      window.localStorage.setItem('condominio_theme_mode', theme);
      const root = document.documentElement;
      root.classList.remove('theme-light', 'theme-dark');
      root.classList.add(`theme-${theme}`);
      document.querySelector('meta[name="color-scheme"]')?.setAttribute('content', theme);
      window.dispatchEvent(
        new StorageEvent('storage', { key: 'condominio_theme_mode', newValue: theme }),
      );
    }, this.target);
    await page.waitForFunction(
      (expected) => document.documentElement.classList.contains(`theme-${expected}`),
      this.target,
    );
    await page.evaluate(async () => {
      await new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      );
      await Promise.allSettled(document.getAnimations().map((anim) => anim.finished));
    });
  }
}

export class ReportPayment implements Task {
  readonly description: string;

  private constructor(
    private readonly monto: string,
    private readonly referencia: string,
  ) {
    this.description = `reportar pago de ${monto} con referencia ${referencia}`;
  }

  static amountWithReference(monto: string, referencia: string): ReportPayment {
    return new ReportPayment(monto, referencia);
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/finanzas/reportar-pago', { waitUntil: 'domcontentloaded' });
    await page.locator('#step-1-monto').fill(this.monto);
    await page.locator('#btn-step-1-next').click();
    await page.locator('#step-2-metodo').selectOption('PAGO_MOVIL');
    await page.locator('#input-referencia').fill(this.referencia);
    await page.locator('#btn-step-2-next').click();
    await page.locator('#btn-submit-pago').click();
    await page.waitForURL('**/dashboard');
    await page.locator('h1').first().waitFor({ state: 'visible' });
  }
}

export class ApprovePendingPayment implements Task {
  readonly description = 'aprobar el primer pago en conciliación de tesorería';

  static first(): ApprovePendingPayment {
    return new ApprovePendingPayment();
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/tesoreria/pagos', { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: 'Aprobar Pago' }).first().click();
    await page.locator('.banner--success').waitFor({ state: 'visible' });
  }
}

export class ExecuteMonthlyClosing implements Task {
  readonly description = 'activar el candado contable mensual en tesorería';

  static now(): ExecuteMonthlyClosing {
    return new ExecuteMonthlyClosing();
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/tesoreria/cierre', { waitUntil: 'domcontentloaded' });
    await page.locator('#btn-open-closing-modal').click();
    await waitForDialogSettled(page, '#modal-confirm-closing');
    await page
      .locator('#modal-confirm-closing')
      .getByRole('button', { name: /Confirmar|Cerrar/i })
      .first()
      .click();
    await page.locator('.banner--success').waitFor({ state: 'visible' });
  }
}

export class EmitBillingAndInspectBreakdown implements Task {
  readonly description = 'emitir facturación mensual y abrir el desglose del recibo';

  static forDefaultPeriod(): EmitBillingAndInspectBreakdown {
    return new EmitBillingAndInspectBreakdown();
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/tesoreria/facturacion', { waitUntil: 'domcontentloaded' });
    await page.locator('#btn-submit-facturacion').click();
    await page.locator('#billing-success-banner').waitFor({ state: 'visible' });
    await page.getByRole('button', { name: 'Ver Desglose' }).first().click();
    await waitForDialogSettled(page, '#modal-recibo-desglose');
  }
}

export class IssueAndVerifySolvency implements Task {
  readonly description = 'emitir certificado de solvencia HMAC y verificar autenticidad';

  static forActiveUnit(): IssueAndVerifySolvency {
    return new IssueAndVerifySolvency();
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/finanzas/solvencia', { waitUntil: 'domcontentloaded' });
    await page.locator('#btn-emitir-solvencia').click();
    await page.locator('#qr-solvencia-badge').waitFor({ state: 'visible' });
    await page.locator('#btn-verificar-solvencia').click();
    await page.locator('#solvencia-verificacion-result').waitFor({
      state: 'visible',
    });
  }
}

export class ReportAndSupportIncident implements Task {
  readonly description: string;

  private constructor(private readonly descripcion: string) {
    this.description = `reportar incidencia "${descripcion}" y adherirse`;
  }

  static withDescription(descripcion: string): ReportAndSupportIncident {
    return new ReportAndSupportIncident(descripcion);
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/incidencias', { waitUntil: 'domcontentloaded' });
    await page.locator('#btn-open-new-incident').click();
    await page.locator('#input-inc-descripcion').fill(this.descripcion);
    await page.locator('#btn-submit-incident').click();
    await page.locator('.banner--success').waitFor({ state: 'visible' });
    await page
      .getByRole('button', { name: /¡Me sumo!/i })
      .first()
      .click();
    await page.locator('.banner--success').waitFor({ state: 'visible' });
  }
}

export class CompleteFirstDailyTask implements Task {
  readonly description = 'marcar como completada la primera tarea de conserjería';

  static now(): CompleteFirstDailyTask {
    return new CompleteFirstDailyTask();
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/operaciones/tareas', { waitUntil: 'domcontentloaded' });
    await page.locator('label[for="chk-task-1"]').click();
    await page.locator('.banner--success').waitFor({ state: 'visible' });
  }
}

export class ActivateFirstPendingResident implements Task {
  readonly description = 'activar al primer usuario fantasma pendiente desde presidencia';

  static now(): ActivateFirstPendingResident {
    return new ActivateFirstPendingResident();
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/admin/usuarios', { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: 'Vincular y Activar Cuenta' }).first().click();
    await page.locator('#ghost-success-banner').waitFor({ state: 'visible' });
  }
}

export class VoteInConsultation implements Task {
  readonly description = 'emitir voto ponderado por alícuota y revisar recibo HMAC';

  static firstOpenOption(): VoteInConsultation {
    return new VoteInConsultation();
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/consultas', { waitUntil: 'domcontentloaded' });
    await page.locator('#btn-open-consulta-1').click();
    await page.waitForURL('**/consultas/1');
    await page.getByTestId('option-card-11').click();
    await page.locator('#btn-cast-vote').click();
    await waitForDialogSettled(page, '#modal-vote-receipt');
  }
}

export class IssueVisitorQrPass implements Task {
  readonly description: string;

  private constructor(
    private readonly visitante: string,
    private readonly cedula: string,
  ) {
    this.description = `emitir pase QR para ${visitante}`;
  }

  static forVisitor(visitante: string, cedula: string): IssueVisitorQrPass {
    return new IssueVisitorQrPass(visitante, cedula);
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/accesos/pases', { waitUntil: 'domcontentloaded' });
    await page.locator('#input-pase-nombre').fill(this.visitante);
    await page.locator('#input-pase-cedula').fill(this.cedula);
    await page.locator('#btn-submit-pase-qr').click();
    await page.locator('#passes-success-banner').waitFor({ state: 'visible' });
  }
}

export class VerifyQrPassAtGatehouse implements Task {
  readonly description: string;

  private constructor(private readonly token: string) {
    this.description = 'verificar pase QR en garita';
  }

  static withToken(token: string): VerifyQrPassAtGatehouse {
    return new VerifyQrPassAtGatehouse(token);
  }

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/operaciones/garita-qr', { waitUntil: 'domcontentloaded' });
    await page.locator('#input-scan-qr-token').fill(this.token);
    await page.locator('#btn-verify-qr').click();
    await page.locator('#qr-scan-success-card, #qr-scan-error-alert').first().waitFor({
      state: 'visible',
    });
  }
}

export class RequestAndCancelAmenity implements Task {
  readonly description = 'solicitar reserva de área social y cancelarla';

  static withReason(motivo: string): RequestAndCancelAmenity {
    return new RequestAndCancelAmenity(motivo);
  }

  private constructor(private readonly motivo: string) {}

  async performAs(actor: Actor): Promise<void> {
    const page = actor.page();
    await page.goto('/reservas/areas', { waitUntil: 'domcontentloaded' });
    await page.locator('#input-reserva-motivo').fill(this.motivo);
    await page.locator('#btn-submit-reserva').click();
    await page
      .locator('#amenities-success-alert, #amenities-error-alert, .alert--success, .alert--error')
      .first()
      .waitFor({
        state: 'visible',
      });
    const cancelBtn = page.getByRole('button', { name: /Cancelar/i }).first();
    if (await cancelBtn.isVisible()) {
      await cancelBtn.click();
      await page.locator('.alert--success, [role="status"]').first().waitFor({ state: 'visible' });
    }
  }
}
