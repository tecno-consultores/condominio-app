// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  canTransitionDisplay,
  closeTopLayerDialog,
  getActiveConsultationTransition,
  prefersReducedMotion,
  resetDisplayTransitionProbeForTests,
  runWithViewTransition,
  setActiveConsultationTransition,
  supportsTopLayerExit,
} from './useViewTransition';

describe('useViewTransition.ts (View Transitions, Top Layer & Reduced Motion)', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    resetDisplayTransitionProbeForTests();
    setActiveConsultationTransition(null);
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: undefined,
    });
  });

  afterEach(() => {
    resetDisplayTransitionProbeForTests();
    vi.restoreAllMocks();
  });

  it('gestiona el identificador de transición activa de Carta Consulta y ejecuta fallback sin startViewTransition', async () => {
    setActiveConsultationTransition(42);
    expect(getActiveConsultationTransition()).toBe(42);

    const heading = document.createElement('h1');
    heading.id = 'target-heading';
    const focusSpy = vi.spyOn(heading, 'focus');
    document.body.appendChild(heading);

    const updateSpy = vi.fn();
    await runWithViewTransition(updateSpy, { focusSelector: '#target-heading' });

    expect(updateSpy).toHaveBeenCalledTimes(1);
    expect(heading.getAttribute('tabindex')).toBe('-1');
    expect(focusSpy).toHaveBeenCalledWith({ preventScroll: true });
    expect(prefersReducedMotion()).toBe(false);
  });

  it('usa document.startViewTransition cuando no hay reduced-motion y respeta prefers-reduced-motion', async () => {
    const startMock = vi.fn((cb: () => void | Promise<void>) => {
      void cb();
      return { finished: Promise.resolve() };
    });
    Object.defineProperty(document, 'startViewTransition', {
      configurable: true,
      writable: true,
      value: startMock,
    });

    const spy = vi.fn();
    await runWithViewTransition(spy);
    expect(startMock).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledTimes(1);

    // Simular prefers-reduced-motion: reduce -> NO llama startViewTransition
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn().mockReturnValue({ matches: true }),
    });
    expect(prefersReducedMotion()).toBe(true);
    await runWithViewTransition(spy);
    expect(startMock).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it('detecta soporte real de transición en display y cierra dialogos Top Layer esperando animaciones activas', async () => {
    // Sin getAnimations en JSDOM -> fallback seguro y cierre inmediato
    expect(canTransitionDisplay()).toBe(false);
    expect(supportsTopLayerExit()).toBe(false);

    const dialog = document.createElement('dialog');
    Object.defineProperty(dialog, 'open', { value: true, configurable: true });
    dialog.close = vi.fn();

    await closeTopLayerDialog(null);
    await closeTopLayerDialog(dialog);
    expect(dialog.close).toHaveBeenCalledTimes(1);

    // Simular navegador con transición real de display (no Firefox 1882408)
    resetDisplayTransitionProbeForTests();
    const animFinished = Promise.resolve();
    const getAnimationsMock = vi.fn().mockReturnValue([{ finished: animFinished }]);
    Element.prototype.getAnimations = getAnimationsMock;

    expect(canTransitionDisplay()).toBe(true);
    expect(supportsTopLayerExit()).toBe(true);

    const dialogAnimated = document.createElement('dialog');
    Object.defineProperty(dialogAnimated, 'open', { value: true, configurable: true });
    dialogAnimated.close = vi.fn();
    dialogAnimated.getAnimations = vi.fn().mockReturnValue([{ finished: Promise.resolve() }]);

    await closeTopLayerDialog(dialogAnimated);
    expect(dialogAnimated.hasAttribute('data-closing')).toBe(false);
    expect(dialogAnimated.close).toHaveBeenCalledTimes(1);

    // Caso sin animaciones activas en cierre
    dialogAnimated.getAnimations = vi.fn().mockReturnValue([]);
    await closeTopLayerDialog(dialogAnimated);
    expect(dialogAnimated.close).toHaveBeenCalledTimes(2);

    const updateAsyncSpy = vi.fn(async () => Promise.resolve());
    await runWithViewTransition(updateAsyncSpy, { focusSelector: '#missing-heading' });
    expect(updateAsyncSpy).toHaveBeenCalledTimes(1);

    // Simular navigator con startViewTransition sin .finished
    const simpleUpdate = vi.fn();
    Object.defineProperty(document, 'startViewTransition', {
      configurable: true,
      writable: true,
      value: vi.fn((cb: () => void) => {
        cb();
        return {};
      }),
    });
    await runWithViewTransition(simpleUpdate);
    expect(simpleUpdate).toHaveBeenCalledTimes(1);

    // Dialogo ya cerrado no ejecuta cierre ni wait
    const closedDialog = document.createElement('dialog');
    closedDialog.close = vi.fn();
    await closeTopLayerDialog(closedDialog);
    expect(closedDialog.close).not.toHaveBeenCalled();

    delete (Element.prototype as Partial<Element>).getAnimations;
  });
});
