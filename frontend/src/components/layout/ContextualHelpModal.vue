<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { useTopLayerDialog } from '../../composables/useTopLayerDialog';
import { useAuthStore } from '../../stores/authStore';
import { getScreenHelp, type ScreenHelpData } from '../../utils/screenHelpCatalog';

const props = defineProps<{
  open: boolean;
  path?: string;
  role?: string | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

let route: { path?: string } | undefined;
try {
  if (typeof useRoute === 'function') {
    route = useRoute();
  }
} catch {
  // Fallback si no está inyectado el provider del router
}

const authStore = useAuthStore();
const dialogRef = ref<HTMLDialogElement | null>(null);

const activePath = computed(() => props.path ?? route?.path ?? '/dashboard');
const activeRole = computed(() => props.role ?? authStore?.userRole ?? 'PROPIETARIO');
const helpData = computed<ScreenHelpData>(() => getScreenHelp(activePath.value, activeRole.value));

const { dialogProps, onPointerDown, onPointerUp, onBackdropClick } = useTopLayerDialog({
  dialogRef,
  isOpen: () => props.open,
  onClose: () => emit('close'),
  unmountsWhenClosed: true,
});

function handleClose(): void {
  emit('close');
}
</script>

<template>
  <dialog
    v-if="open"
    id="dialog-contextual-help"
    ref="dialogRef"
    v-bind="dialogProps"
    class="help-dialog top-layer-dialog"
    aria-labelledby="help-screen-title"
    aria-describedby="help-screen-purpose"
    @close="handleClose"
    @pointerdown="onPointerDown"
    @pointerup="onPointerUp"
    @click="onBackdropClick"
  >
    <div class="help-dialog__card">
      <header class="help-dialog__header">
        <div class="help-dialog__header-text">
          <span class="help-dialog__badge">Guía Contextual 11X</span>
          <h2 id="help-screen-title" class="help-dialog__title">
            {{ helpData.title }}
          </h2>
        </div>
        <button
          id="btn-close-help"
          type="button"
          class="help-dialog__close-btn"
          aria-label="Cerrar ayuda contextual"
          @click="handleClose"
        >
          <span aria-hidden="true">&times;</span>
        </button>
      </header>

      <section
        class="help-dialog__body"
        tabindex="0"
        :aria-label="`Detalles y pasos de ${helpData.title}`"
      >
        <div class="help-dialog__purpose-card">
          <p id="help-screen-purpose" class="help-dialog__purpose">
            {{ helpData.purpose }}
          </p>
        </div>

        <section class="help-dialog__section" aria-labelledby="help-steps-heading">
          <h3 id="help-steps-heading" class="help-dialog__section-title">
            Paso a Paso Recomendado
          </h3>
          <ol id="help-steps-list" class="help-steps-list">
            <li
              v-for="(step, index) in helpData.steps"
              :key="`step-${index}`"
              class="help-steps-item"
            >
              <span class="help-steps-item__num" aria-hidden="true">{{ index + 1 }}</span>
              <span class="help-steps-item__text">{{ step }}</span>
            </li>
          </ol>
        </section>

        <section
          v-if="helpData.tips && helpData.tips.length > 0"
          class="help-dialog__section help-dialog__section--tips"
          aria-labelledby="help-tips-heading"
        >
          <h3
            id="help-tips-heading"
            class="help-dialog__section-title help-dialog__section-title--tips"
          >
            Consejos y Puntos Clave
          </h3>
          <ul id="help-tips-list" class="help-tips-list">
            <li v-for="(tip, index) in helpData.tips" :key="`tip-${index}`" class="help-tips-item">
              <span class="help-tips-item__icon" aria-hidden="true">💡</span>
              <span class="help-tips-item__text">{{ tip }}</span>
            </li>
          </ul>
        </section>
      </section>

      <footer class="help-dialog__footer">
        <button type="button" autofocus class="help-dialog__action-btn" @click="handleClose">
          Entendido
        </button>
      </footer>
    </div>
  </dialog>
</template>

<style scoped>
.help-dialog[open] {
  border: none;
  border-radius: var(--radius-lg);
  padding: 0;
  background: var(--surface-elevated);
  color: var(--text-primary);
  box-shadow: var(--shadow-modal);
  inline-size: min(100% - 1.5rem, 38rem);
  max-block-size: min(85dvh, 44rem);
  overscroll-behavior: contain;
}

.help-dialog::backdrop {
  overflow: hidden;
  backdrop-filter: blur(4px);
  overscroll-behavior: contain;
}

.help-dialog__card {
  display: flex;
  flex-direction: column;
  background-color: var(--surface-elevated);
  border-radius: var(--radius-lg);
  max-block-size: min(85dvh, 44rem);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.help-dialog__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: clamp(1rem, 2.5cqi, 1.5rem);
  background: linear-gradient(180deg, var(--surface-subtle) 0%, var(--surface-elevated) 100%);
  border-bottom: 1px solid var(--border-subtle);
  gap: 1rem;
}

.help-dialog__header-text {
  flex: 1;
}

.help-dialog__badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--brand-accent);
  background-color: var(--brand-tint);
  padding: 0.2rem 0.5rem;
  border-radius: 0.375rem;
  margin-bottom: 0.35rem;
}

.help-dialog__title {
  font-size: clamp(1.125rem, 3cqi, 1.375rem);
  font-weight: 700;
  line-height: 1.3;
  color: var(--text-primary);
  margin: 0;
  text-wrap: balance;
}

.help-dialog__close-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 2.75rem;
  block-size: 2.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-card);
  color: var(--text-secondary);
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
  padding: 0;
}

.help-dialog__close-btn:hover {
  background-color: var(--surface-subtle);
  color: var(--text-primary);
  border-color: var(--brand-accent);
}

.help-dialog__body {
  padding: clamp(1rem, 2.5cqi, 1.5rem);
  overflow-y: auto;
  overscroll-behavior: contain;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  flex: 1;
}

.help-dialog__purpose-card {
  background-color: var(--surface-subtle);
  border-left: 4px solid var(--brand-accent);
  padding: 0.875rem 1rem;
  border-radius: 0 0.5rem 0.5rem 0;
}

.help-dialog__purpose {
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.5;
  color: var(--text-secondary);
  max-inline-size: 65ch;
  text-wrap: pretty;
}

.help-dialog__section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.help-dialog__section-title {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary);
}

.help-dialog__section-title--tips {
  color: var(--status-warn-text);
}

.help-steps-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.help-steps-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  transition: border-color 0.15s ease;
}

.help-steps-item:hover {
  border-color: var(--border-control);
}

.help-steps-item__num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 1.625rem;
  block-size: 1.625rem;
  border-radius: 50%;
  background-color: var(--brand-600);
  color: var(--text-on-accent);
  font-size: 0.8125rem;
  font-weight: 700;
  flex-shrink: 0;
}

.help-steps-item__text {
  font-size: 0.9rem;
  line-height: 1.45;
  color: var(--text-primary);
  max-inline-size: 65ch;
  text-wrap: pretty;
}

.help-dialog__section--tips {
  background-color: var(--status-warn-bg);
  border: 1px solid var(--status-warn-border);
  border-radius: 0.625rem;
  padding: 0.875rem 1rem;
}

.help-tips-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.help-tips-item {
  display: flex;
  align-items: flex-start;
  gap: 0.625rem;
}

.help-tips-item__icon {
  font-size: 1rem;
  line-height: 1.3;
  flex-shrink: 0;
}

.help-tips-item__text {
  font-size: 0.875rem;
  line-height: 1.4;
  color: var(--status-warn-text);
  max-inline-size: 65ch;
  text-wrap: pretty;
}

.help-dialog__footer {
  display: flex;
  justify-content: flex-end;
  padding: clamp(0.75rem, 2cqi, 1rem) clamp(1rem, 2.5cqi, 1.5rem);
  background-color: var(--surface-subtle);
  border-top: 1px solid var(--border-subtle);
}

.help-dialog__action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-block-size: 2.75rem;
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: none;
  background-color: var(--brand-600);
  color: var(--text-on-accent);
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.help-dialog__action-btn:hover {
  background-color: var(--brand-700);
}

@media (max-width: 639px) {
  .help-dialog[open] {
    margin: auto 0 0 0;
    inline-size: 100%;
    max-inline-size: 100%;
    max-block-size: 88dvh;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  }

  .help-dialog__card {
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    max-block-size: 88dvh;
  }
}
</style>
