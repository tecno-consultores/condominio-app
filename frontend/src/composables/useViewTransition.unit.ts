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

async function flushMicrotasks(): Promise<void> {
  for (let i = 0; i < 8; i += 1) {
    await Promise.resolve();
  }
}

function trackCompletion(promise: Promise<unknown>): { isDone: () => boolean } {
  let done = false;
  void promise.then(() => {
    done = true;
  });
  return { isDone: () => done };
}

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
    vi.useRealTimers();
    delete (Element.prototype as Partial<Element>).getAnimations;
    delete (document as unknown as Partial<Document>).startViewTransition;
    resetDisplayTransitionProbeForTests();
    vi.unstubAllGlobals();
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

    // Elemento que ya tiene tabindex conserva su tabindex y rama sin document.body
    const headingWithTabindex = document.createElement('h2');
    headingWithTabindex.id = 'existing-tab';
    headingWithTabindex.setAttribute('tabindex', '0');
    document.body.appendChild(headingWithTabindex);
    await runWithViewTransition(vi.fn(), { focusSelector: '#existing-tab' });
    expect(headingWithTabindex.getAttribute('tabindex')).toBe('0');

    resetDisplayTransitionProbeForTests();
    const originalBody = document.body;
    Object.defineProperty(document, 'body', { configurable: true, value: null });
    expect(canTransitionDisplay()).toBe(false);
    Object.defineProperty(document, 'body', { configurable: true, value: originalBody });

    delete (Element.prototype as Partial<Element>).getAnimations;
  });

  it('evalúa prefersReducedMotion con consulta exacta y retorna false sin window', () => {
    const matchMediaMock = vi.fn((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
    }));
    vi.stubGlobal('matchMedia', matchMediaMock);

    expect(prefersReducedMotion()).toBe(true);
    expect(matchMediaMock).toHaveBeenCalledWith('(prefers-reduced-motion: reduce)');

    vi.stubGlobal('window', undefined);
    try {
      expect(prefersReducedMotion()).toBe(false);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('valida sonda DOM de canTransitionDisplay, caché y retorno seguro en SSR', () => {
    vi.stubGlobal('document', undefined);
    try {
      expect(canTransitionDisplay()).toBe(false);
    } finally {
      vi.unstubAllGlobals();
    }

    let observedConnected = false;
    let observedPosition = '';
    let observedOpacity = '';
    let observedDisplay = '';
    const emptyAnimMock = vi.fn(function (this: HTMLElement) {
      observedConnected = this.isConnected;
      observedPosition = this.style.position;
      observedOpacity = this.style.opacity;
      observedDisplay = this.style.display;
      return [] as Animation[];
    });
    Element.prototype.getAnimations = emptyAnimMock;

    expect(canTransitionDisplay()).toBe(false);
    expect(observedConnected).toBe(true);
    expect(observedPosition).toBe('fixed');
    expect(observedOpacity).toBe('0');
    expect(observedDisplay).toBe('none');
    expect(document.body.children).toHaveLength(0);

    // Segunda llamada usa caché sin volver a ejecutar la sonda
    expect(canTransitionDisplay()).toBe(false);
    expect(emptyAnimMock).toHaveBeenCalledTimes(1);

    resetDisplayTransitionProbeForTests();
    const activeAnimMock = vi.fn().mockReturnValue([{} as Animation]);
    Element.prototype.getAnimations = activeAnimMock;
    expect(canTransitionDisplay()).toBe(true);
    expect(canTransitionDisplay()).toBe(true);
    expect(activeAnimMock).toHaveBeenCalledTimes(1);
  });

  it('ejecuta updateDom en SSR, espera promesas reales y protege focusElementSafely', async () => {
    let ssrDone = false;
    vi.stubGlobal('document', undefined);
    try {
      await runWithViewTransition(async () => {
        await Promise.resolve();
        ssrDone = true;
      });
    } finally {
      vi.unstubAllGlobals();
    }
    expect(ssrDone).toBe(true);

    let asyncDone = false;
    await runWithViewTransition(async () => {
      await Promise.resolve();
      await Promise.resolve();
      asyncDone = true;
    });
    expect(asyncDone).toBe(true);

    const querySpy = vi.spyOn(document, 'querySelector');
    const heading = document.createElement('h1');
    heading.id = 'sync-focus-target';
    const focusSpy = vi.spyOn(heading, 'focus');
    document.body.appendChild(heading);

    await runWithViewTransition(() => undefined);
    expect(querySpy).not.toHaveBeenCalled();

    // Actualización síncrona enfoca de inmediato sin suspenderse en await
    const syncPromise = runWithViewTransition(() => undefined, {
      focusSelector: '#sync-focus-target',
    });
    expect(focusSpy).toHaveBeenCalledTimes(1);
    await syncPromise;

    const div = document.createElement('div');
    div.id = 'no-focus-fn';
    Object.defineProperty(div, 'focus', { configurable: true, value: undefined });
    document.body.appendChild(div);
    await runWithViewTransition(() => undefined, { focusSelector: '#no-focus-fn' });

    // Si document desaparece durante updateDom, focusElementSafely retorna sin fallar
    try {
      await runWithViewTransition(
        () => {
          vi.stubGlobal('document', undefined);
        },
        { focusSelector: '#sync-focus-target' },
      );
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('espera transition.finished, tolera retorno undefined y captura rechazos', async () => {
    const heading = document.createElement('h1');
    heading.id = 'vt-focus';
    const focusSpy = vi.spyOn(heading, 'focus');
    document.body.appendChild(heading);

    Object.defineProperty(document, 'startViewTransition', {
      configurable: true,
      writable: true,
      value: vi.fn((cb: () => void) => {
        cb();
        return undefined;
      }),
    });
    await runWithViewTransition(() => undefined, { focusSelector: '#vt-focus' });
    expect(focusSpy).toHaveBeenCalledTimes(1);

    let resolveTransition!: () => void;
    Object.defineProperty(document, 'startViewTransition', {
      configurable: true,
      writable: true,
      value: vi.fn((cb: () => void) => {
        cb();
        return {
          finished: new Promise<void>((resolve) => {
            resolveTransition = resolve;
          }),
        };
      }),
    });

    const pending = runWithViewTransition(() => undefined, { focusSelector: '#vt-focus' });
    const pendingState = trackCompletion(pending);
    await Promise.resolve();
    await Promise.resolve();
    expect(pendingState.isDone()).toBe(false);
    expect(focusSpy).toHaveBeenCalledTimes(1);

    resolveTransition();
    await pending;
    expect(pendingState.isDone()).toBe(true);
    expect(focusSpy).toHaveBeenCalledTimes(2);

    Object.defineProperty(document, 'startViewTransition', {
      configurable: true,
      writable: true,
      value: vi.fn((cb: () => void) => {
        cb();
        return { finished: Promise.reject(new Error('transition aborted')) };
      }),
    });
    await runWithViewTransition(() => undefined, { focusSelector: '#vt-focus' });
    expect(focusSpy).toHaveBeenCalledTimes(3);
  });

  it('maneja close/getAnimations ausentes, sin timeout ni anim.finished prematuro', async () => {
    const noCloseFallback = { open: true } as unknown as HTMLDialogElement;
    await closeTopLayerDialog(noCloseFallback);

    resetDisplayTransitionProbeForTests();
    Element.prototype.getAnimations = vi.fn().mockReturnValue([{} as Animation]);
    expect(supportsTopLayerExit()).toBe(true);

    const dialogWithoutGetAnim = document.createElement('dialog');
    Object.defineProperty(dialogWithoutGetAnim, 'open', { value: true, configurable: true });
    Object.defineProperty(dialogWithoutGetAnim, 'getAnimations', {
      value: undefined,
      configurable: true,
    });
    dialogWithoutGetAnim.close = vi.fn();
    await closeTopLayerDialog(dialogWithoutGetAnim);
    expect(dialogWithoutGetAnim.close).toHaveBeenCalledTimes(1);

    const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');
    const noCloseAnimated = {
      open: true,
      setAttribute: vi.fn(),
      removeAttribute: vi.fn(),
      getAnimations: vi.fn().mockReturnValue([]),
    } as unknown as HTMLDialogElement;
    await closeTopLayerDialog(noCloseAnimated);
    expect(setTimeoutSpy).not.toHaveBeenCalled();

    vi.useFakeTimers();
    const dialogPending = document.createElement('dialog');
    Object.defineProperty(dialogPending, 'open', { value: true, configurable: true });
    dialogPending.close = vi.fn();
    let resolveAnim!: () => void;
    const pendingAnim = {
      finished: new Promise<void>((resolve) => {
        resolveAnim = resolve;
      }),
    } as unknown as Animation;
    dialogPending.getAnimations = vi.fn().mockReturnValue([pendingAnim]);

    const pendingState = trackCompletion(closeTopLayerDialog(dialogPending, 5_000));
    await flushMicrotasks();
    expect(dialogPending.getAttribute('data-closing')).toBe('');
    expect(dialogPending.close).not.toHaveBeenCalled();
    expect(pendingState.isDone()).toBe(false);

    resolveAnim();
    await flushMicrotasks();
    expect(pendingState.isDone()).toBe(true);
    expect(dialogPending.hasAttribute('data-closing')).toBe(false);
    expect(dialogPending.close).toHaveBeenCalledTimes(1);
  });

  it('aplica timeoutMs cuando la animación de cierre no finaliza a tiempo', async () => {
    vi.useFakeTimers();
    Element.prototype.getAnimations = vi.fn().mockReturnValue([{} as Animation]);

    const dialogStuck = document.createElement('dialog');
    Object.defineProperty(dialogStuck, 'open', { value: true, configurable: true });
    dialogStuck.close = vi.fn();
    const stuckAnim = {
      finished: new Promise<void>(() => undefined),
    } as unknown as Animation;
    dialogStuck.getAnimations = vi.fn().mockReturnValue([stuckAnim]);

    const stuckState = trackCompletion(closeTopLayerDialog(dialogStuck, 280));

    await vi.advanceTimersByTimeAsync(279);
    expect(stuckState.isDone()).toBe(false);
    expect(dialogStuck.close).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(1);
    expect(stuckState.isDone()).toBe(true);
    expect(dialogStuck.hasAttribute('data-closing')).toBe(false);
    expect(dialogStuck.close).toHaveBeenCalledTimes(1);
  });
});
