<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

interface CommandLikeEvent extends Event {
  command?: string;
  source?: EventTarget | null;
}

const props = withDefaults(
  defineProps<{
    id?: string;
    targetId: string;
    label: string;
  }>(),
  {
    id: undefined,
  },
);

const COPY_RESET_MS = 2000;
let lastAnnouncement = '';

const buttonRef = ref<HTMLButtonElement | null>(null);
const tipRef = ref<HTMLSpanElement | null>(null);
const statusState = ref<'idle' | 'copied' | 'failed'>('idle');
let activeTimer: ReturnType<typeof setTimeout> | null = null;

const glyph = computed<string>(() => {
  if (statusState.value === 'copied') return '✓';
  if (statusState.value === 'failed') return '!';
  return '⧉';
});

function supportsInvokerCommands(): boolean {
  return typeof window !== 'undefined' && 'CommandEvent' in window;
}

function readTargetText(targetId: string, eventTarget?: EventTarget | null): string {
  const element =
    eventTarget instanceof HTMLElement ? eventTarget : document.getElementById(targetId);
  if (!element) return '';
  if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
    return element.value.trim();
  }
  return (element.innerText || element.textContent || '').trim();
}

function legacyCopy(text: string): boolean {
  const field = document.createElement('textarea');
  field.value = text;
  field.setAttribute('readonly', '');
  field.style.cssText = 'position:fixed;inset-block-start:0;opacity:0';
  document.body.append(field);
  field.select();
  try {
    return typeof document.execCommand === 'function' && document.execCommand('copy');
  } finally {
    field.remove();
  }
}

async function writeToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fallback para contextos HTTP efímeros o permisos denegados
  }
  return legacyCopy(text);
}

function clearFeedback(): void {
  activeTimer = null;
  statusState.value = 'idle';
  buttonRef.value?.removeAttribute('data-copied');
  buttonRef.value?.removeAttribute('data-failed');
  if (tipRef.value) {
    tipRef.value.textContent = '';
  }
}

function nextAnnouncement(ok: boolean): string {
  let message = ok ? 'Copiado' : 'Error al copiar';
  if (message === lastAnnouncement) {
    message += '\u00A0';
  }
  lastAnnouncement = message;
  return message;
}

function reportCopyResult(ok: boolean): void {
  const button = buttonRef.value;
  const tip = tipRef.value;
  if (!button || !tip) return;

  if (activeTimer !== null) {
    clearTimeout(activeTimer);
  }
  button.removeAttribute('data-copied');
  button.removeAttribute('data-failed');
  tip.textContent = '';
  void button.offsetWidth;

  statusState.value = ok ? 'copied' : 'failed';
  button.setAttribute(ok ? 'data-copied' : 'data-failed', '');
  const message = nextAnnouncement(ok);
  requestAnimationFrame(() => {
    if (tipRef.value) {
      tipRef.value.textContent = message;
    }
  });
  activeTimer = setTimeout(clearFeedback, COPY_RESET_MS);
}

async function performCopy(eventTarget?: EventTarget | null): Promise<void> {
  const text = readTargetText(props.targetId, eventTarget);
  if (!text) return;
  const ok = await writeToClipboard(text);
  reportCopyResult(ok);
}

function handleFallbackClick(): void {
  if (supportsInvokerCommands()) return;
  void performCopy();
}

function onDocumentCommand(event: Event): void {
  const cmdEvent = event as CommandLikeEvent;
  if (cmdEvent.source !== buttonRef.value || cmdEvent.command !== '--copy') return;
  void performCopy(cmdEvent.target);
}

onMounted(() => {
  if (supportsInvokerCommands()) {
    document.addEventListener('command', onDocumentCommand, true);
  }
});

onBeforeUnmount(() => {
  if (activeTimer !== null) {
    clearTimeout(activeTimer);
    activeTimer = null;
  }
  document.removeEventListener('command', onDocumentCommand, true);
});
</script>

<template>
  <span class="copy-control">
    <button
      :id="props.id"
      ref="buttonRef"
      type="button"
      class="copy-control__button"
      command="--copy"
      :commandfor="props.targetId"
      :aria-label="props.label"
      @click="handleFallbackClick"
    >
      <span class="copy-control__icon" aria-hidden="true">{{ glyph }}</span>
    </button>
    <span ref="tipRef" class="copy-control__tip" role="status"></span>
  </span>
</template>

<style scoped>
.copy-control {
  position: relative;
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

.copy-control__button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-inline-size: 2rem;
  min-block-size: 2rem;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm, 0.5rem);
  border: 1px solid var(--border-control, #64748b);
  background-color: var(--surface-card, #ffffff);
  color: var(--text-primary, #0f172a);
  font-size: 0.875rem;
  font-weight: 700;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease,
    color 0.15s ease;
}

.copy-control__button:hover {
  background-color: var(--brand-tint, #f0f9ff);
  border-color: var(--brand-accent, #0369a1);
}

.copy-control__button[data-copied] {
  background-color: var(--status-ok-bg, #dcfce7);
  color: var(--status-ok-text, #166534);
  border-color: var(--status-ok-border, #16a34a);
}

.copy-control__button[data-failed] {
  background-color: var(--status-danger-bg, #fef2f2);
  color: var(--status-danger-text, #991b1b);
  border-color: var(--status-danger-border, #dc2626);
}

.copy-control__tip {
  position: absolute;
  inset-block-end: calc(100% + 0.3rem);
  inset-inline-end: 0;
  z-index: 4;
  pointer-events: none;
  opacity: 0;
  white-space: nowrap;
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 1.2;
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-sm, 0.5rem);
  border: 1px solid var(--border-subtle, #cbd5e1);
  background-color: var(--surface-elevated, #ffffff);
  color: var(--text-primary, #0f172a);
  box-shadow: var(--shadow-card);
  transition: opacity 0.15s ease;
}

.copy-control__tip:not(:empty) {
  opacity: 1;
}

.copy-control__button[data-copied] + .copy-control__tip:not(:empty) {
  background-color: var(--status-ok-bg, #dcfce7);
  color: var(--status-ok-text, #166534);
  border-color: var(--status-ok-border, #16a34a);
}

.copy-control__button[data-failed] + .copy-control__tip:not(:empty) {
  background-color: var(--status-danger-bg, #fef2f2);
  color: var(--status-danger-text, #991b1b);
  border-color: var(--status-danger-border, #dc2626);
}

@media (pointer: coarse) {
  .copy-control__button {
    min-inline-size: 2.75rem;
    min-block-size: 2.75rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .copy-control__button {
    transition: none;
  }
}
</style>
