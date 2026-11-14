// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import AxeBuilder from '@axe-core/playwright';
import type { Actor, Question } from './core';

export interface AccessibilityViolationSummary {
  id: string;
  impact: string;
  help: string;
  nodes: string[];
}

export interface GeometryAuditResult {
  hasHorizontalOverflow: boolean;
  scrollWidth: number;
  innerWidth: number;
  footerPosition: string | null;
  footerOccluded: boolean;
  occludedControls: string[];
}

export class CurrentPathname implements Question<string> {
  readonly description = 'consultar la ruta URL actual del navegador';

  static value(): CurrentPathname {
    return new CurrentPathname();
  }

  async answeredBy(actor: Actor): Promise<string> {
    return new URL(actor.page().url()).pathname;
  }
}

export class VisibleHeading implements Question<string> {
  readonly description = 'leer el encabezado principal h1 visible';

  static text(): VisibleHeading {
    return new VisibleHeading();
  }

  async answeredBy(actor: Actor): Promise<string> {
    const heading = actor.page().locator('h1').first();
    await heading.waitFor({ state: 'visible' });
    return (await heading.innerText()).trim();
  }
}

export class TextOfElement implements Question<string> {
  readonly description: string;

  private constructor(private readonly selector: string) {
    this.description = `leer texto visible de ${selector}`;
  }

  static matching(selector: string): TextOfElement {
    return new TextOfElement(selector);
  }

  async answeredBy(actor: Actor): Promise<string> {
    const el = actor.page().locator(this.selector).first();
    await el.waitFor({ state: 'visible' });
    return (await el.innerText()).trim();
  }
}

export class IsElementVisible implements Question<boolean> {
  readonly description: string;

  private constructor(private readonly selector: string) {
    this.description = `verificar visibilidad de ${selector}`;
  }

  static matching(selector: string): IsElementVisible {
    return new IsElementVisible(selector);
  }

  async answeredBy(actor: Actor): Promise<boolean> {
    return actor.page().locator(this.selector).first().isVisible();
  }
}

export class CurrentColorScheme implements Question<string> {
  readonly description = 'consultar el esquema de color activo en :root';

  static mode(): CurrentColorScheme {
    return new CurrentColorScheme();
  }

  async answeredBy(actor: Actor): Promise<string> {
    return actor
      .page()
      .evaluate(() =>
        document.documentElement.classList.contains('theme-dark') ? 'dark' : 'light',
      );
  }
}

export class AxeCriticalOrSeriousViolations implements Question<AccessibilityViolationSummary[]> {
  readonly description = 'ejecutar auditoría WCAG 2.1 AA con Axe-Core';

  static detected(): AxeCriticalOrSeriousViolations {
    return new AxeCriticalOrSeriousViolations();
  }

  async answeredBy(actor: Actor): Promise<AccessibilityViolationSummary[]> {
    const page = actor.page();
    await page.evaluate(() => document.fonts.ready);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    return results.violations
      .filter((v) => v.impact === 'critical' || v.impact === 'serious')
      .map((v) => ({
        id: v.id,
        impact: v.impact ?? 'unknown',
        help: v.help,
        nodes: v.nodes.flatMap((n) => n.target.map(String)),
      }));
  }
}

export class ViewportGeometryAudit implements Question<GeometryAuditResult> {
  readonly description =
    'auditar desbordamiento horizontal, footer en flujo y oclusión por barras fijas vía getBoundingClientRect()';

  static snapshot(): ViewportGeometryAudit {
    return new ViewportGeometryAudit();
  }

  async answeredBy(actor: Actor): Promise<GeometryAuditResult> {
    const page = actor.page();
    const baseMetrics = await page.evaluate(async () => {
      const nextFrame = (): Promise<void> =>
        new Promise((resolve) => requestAnimationFrame(() => resolve()));
      const visibleRect = (sel: string): DOMRect | null => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const st = getComputedStyle(el);
        if (st.display === 'none' || st.visibility === 'hidden') return null;
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 ? r : null;
      };

      await document.fonts.ready;
      window.scrollTo(0, document.body.scrollHeight);
      await nextFrame();
      await nextFrame();

      const scrollWidth = document.documentElement.scrollWidth;
      const innerWidth = window.innerWidth;
      const footer = document.querySelector('#app-inflow-footer');
      const footerRect = visibleRect('#app-inflow-footer');
      const navRect = visibleRect('#mobile-bottom-nav');

      let footerOccluded = false;
      if (footerRect && navRect) {
        const hitY = footerRect.bottom > navRect.top + 1;
        const hitX = navRect.right > footerRect.left && navRect.left < footerRect.right;
        footerOccluded = hitY && hitX;
      }
      return {
        hasHorizontalOverflow: scrollWidth > innerWidth,
        scrollWidth,
        innerWidth,
        footerPosition: footer ? getComputedStyle(footer).position : null,
        footerOccluded,
      };
    });

    const occludedControls = await page.evaluate(async () => {
      const nextFrame = (): Promise<void> =>
        new Promise((resolve) => requestAnimationFrame(() => resolve()));
      const isVisible = (el: Element): boolean => {
        const st = getComputedStyle(el);
        if (st.display === 'none' || st.visibility === 'hidden') return false;
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      };
      const isInteractiveSkipped = (el: Element): boolean =>
        el.id === 'fab-reportar-pago' ||
        Boolean(el.closest('#mobile-bottom-nav, .app-header, dialog:not([open])'));

      const fixedChrome = ['#mobile-bottom-nav', '#fab-reportar-pago', '.app-header']
        .map((sel) => ({ sel, el: document.querySelector(sel) }))
        .filter((item): item is { sel: string; el: Element } =>
          Boolean(item.el && isVisible(item.el)),
        );

      const occluded: string[] = [];
      const selector = 'main button, main a[href], section button, form button[type="submit"]';
      for (const node of Array.from(document.querySelectorAll(selector))) {
        if (isInteractiveSkipped(node) || !isVisible(node)) continue;
        node.scrollIntoView({ block: 'center', inline: 'nearest' });
        await nextFrame();
        const r = node.getBoundingClientRect();
        const cx = r.left + r.width / 2;
        const cy = r.top + r.height / 2;
        if (cy < 0 || cy > window.innerHeight || cx < 0 || cx > window.innerWidth) continue;

        const stack = document.elementsFromPoint(cx, cy);
        const blocker = fixedChrome.find(
          (c) => c.el !== node && !node.contains(c.el) && stack.some((t) => c.el.contains(t)),
        );
        if (blocker) {
          occluded.push(`${node.id || node.textContent?.trim() || node.tagName} <- ${blocker.sel}`);
        }
      }
      window.scrollTo(0, 0);
      return occluded;
    });

    return {
      ...baseMetrics,
      occludedControls,
    };
  }
}
