// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { ref } from 'vue';

interface ViewTransitionLike {
  finished?: Promise<unknown>;
}

interface StartViewTransitionHost {
  startViewTransition?: (callback: () => unknown) => ViewTransitionLike;
}

const activeConsultationTransitionId = ref<number | null>(null);
let displayTransitionProbeResult: boolean | null = null;

export function setActiveConsultationTransition(id: number | null): void {
  activeConsultationTransitionId.value = id;
}

export function getActiveConsultationTransition(): number | null {
  return activeConsultationTransitionId.value;
}

export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false;
  }
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function resetDisplayTransitionProbeForTests(): void {
  displayTransitionProbeResult = null;
}

export function canTransitionDisplay(): boolean {
  if (displayTransitionProbeResult !== null) {
    return displayTransitionProbeResult;
  }
  if (typeof document === 'undefined' || !document.body) {
    return false;
  }
  const probe = document.createElement('div');
  if (typeof probe.getAnimations !== 'function') {
    displayTransitionProbeResult = false;
    return false;
  }
  probe.style.cssText =
    'position:fixed;opacity:0;pointer-events:none;transition:display 0.1s allow-discrete;';
  document.body.appendChild(probe);
  void getComputedStyle(probe).display;
  probe.style.display = 'none';
  displayTransitionProbeResult = probe.getAnimations().length > 0;
  probe.remove();
  return displayTransitionProbeResult;
}

export function supportsTopLayerExit(): boolean {
  return canTransitionDisplay() && !prefersReducedMotion();
}

function focusElementSafely(focusSelector?: string): void {
  if (!focusSelector || typeof document === 'undefined') {
    return;
  }
  const el = document.querySelector<HTMLElement>(focusSelector);
  if (!el) {
    return;
  }
  if (!el.hasAttribute('tabindex')) {
    el.setAttribute('tabindex', '-1');
  }
  if (typeof el.focus === 'function') {
    el.focus({ preventScroll: true });
  }
}

export async function runWithViewTransition(
  updateDom: () => unknown,
  options?: { focusSelector?: string },
): Promise<void> {
  if (typeof document === 'undefined') {
    await updateDom();
    return;
  }
  const doc = document as unknown as StartViewTransitionHost;
  if (prefersReducedMotion() || typeof doc.startViewTransition !== 'function') {
    const maybePromise = updateDom();
    if (maybePromise instanceof Promise) {
      await maybePromise;
    }
    focusElementSafely(options?.focusSelector);
    return;
  }
  const transition = doc.startViewTransition(updateDom);
  if (transition?.finished) {
    await transition.finished.catch(() => undefined);
  }
  focusElementSafely(options?.focusSelector);
}

export async function closeTopLayerDialog(
  dialog: HTMLDialogElement | null | undefined,
  timeoutMs = 280,
): Promise<void> {
  if (!dialog || !dialog.open) {
    return;
  }
  if (!supportsTopLayerExit() || typeof dialog.getAnimations !== 'function') {
    dialog.close?.();
    return;
  }
  dialog.setAttribute('data-closing', '');
  const animations = dialog.getAnimations();
  if (animations.length > 0) {
    const waitAnimations = Promise.allSettled(animations.map((anim) => anim.finished));
    const waitTimeout = new Promise<void>((resolve) => {
      setTimeout(resolve, timeoutMs);
    });
    await Promise.race([waitAnimations, waitTimeout]);
  }
  dialog.removeAttribute('data-closing');
  dialog.close?.();
}
