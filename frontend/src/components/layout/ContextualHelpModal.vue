<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
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

function openModalElement(): void {
  const el = dialogRef.value;
  if (el && typeof el.showModal === 'function' && !el.open) {
    el.showModal();
  }
}

onMounted(() => {
  if (props.open) {
    openModalElement();
  }
});

watch(
  () => props.open,
  async (isOpen) => {
    if (!isOpen) {
      if (dialogRef.value?.open) {
        dialogRef.value.close();
      }
      return;
    }
    await nextTick();
    openModalElement();
  },
);

let pressedOutside: boolean | null = null;

function hasNativeClosedBy(): boolean {
  return typeof HTMLDialogElement !== 'undefined' && 'closedBy' in HTMLDialogElement.prototype;
}

function isOutsideDialog(
  event: { clientX: number; clientY: number },
  dialog: HTMLDialogElement,
): boolean {
  const rect = dialog.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return false;
  return (
    event.clientX < rect.left ||
    event.clientX > rect.right ||
    event.clientY < rect.top ||
    event.clientY > rect.bottom
  );
}

function handlePointerDown(event: PointerEvent): void {
  const dialog = dialogRef.value;
  if (!dialog || hasNativeClosedBy()) return;
  pressedOutside = isOutsideDialog(event, dialog);
}

function handlePointerUp(event: PointerEvent): void {
  const dialog = dialogRef.value;
  if (!dialog || hasNativeClosedBy()) return;
  if (pressedOutside === true && isOutsideDialog(event, dialog)) {
    pressedOutside = null;
    emit('close');
  }
}

function handleBackdropClick(event: MouseEvent): void {
  const dialog = dialogRef.value;
  if (!dialog || hasNativeClosedBy()) return;
  if (pressedOutside !== null) {
    pressedOutside = null;
    return;
  }
  if (event.target === dialog && isOutsideDialog(event, dialog)) {
    emit('close');
  }
}

function handleClose(): void {
  emit('close');
}
</script>

<template>
  <dialog
    v-if="open"
    id="dialog-contextual-help"
    ref="dialogRef"
    v-bind="{ closedby: 'any' }"
    class="help-dialog"
    aria-labelledby="help-screen-title"
    aria-describedby="help-screen-purpose"
    @close="handleClose"
    @pointerdown="handlePointerDown"
    @pointerup="handlePointerUp"
    @click="handleBackdropClick"
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
dialog:modal {
  overscroll-behavior: contain;
}

.help-dialog[open] {
  border: none;
  border-radius: 1rem;
  padding: 0;
  background: transparent;
  color: #0f172a;
  box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.25);
  inline-size: min(100% - 1.5rem, 38rem);
  max-block-size: min(85dvh, 44rem);
  overscroll-behavior: contain;
  margin: auto;
}

.help-dialog::backdrop {
  overflow: hidden;
  background-color: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  overscroll-behavior: contain;
}

.help-dialog__card {
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  border-radius: 1rem;
  max-block-size: min(85dvh, 44rem);
  overflow: hidden;
  border: 1px solid #e2e8f0;
}

.help-dialog__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: clamp(1rem, 2.5cqi, 1.5rem);
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  border-bottom: 1px solid #e2e8f0;
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
  color: #0369a1;
  background-color: #e0f2fe;
  padding: 0.2rem 0.5rem;
  border-radius: 0.375rem;
  margin-bottom: 0.35rem;
}

.help-dialog__title {
  font-size: clamp(1.125rem, 3cqi, 1.375rem);
  font-weight: 700;
  line-height: 1.3;
  color: #0f172a;
  margin: 0;
  text-wrap: balance;
}

.help-dialog__close-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 2.25rem;
  block-size: 2.25rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  background-color: #ffffff;
  color: #64748b;
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
  padding: 0;
}

.help-dialog__close-btn:hover {
  background-color: #f1f5f9;
  color: #0f172a;
  border-color: #94a3b8;
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
  background-color: #f8fafc;
  border-left: 4px solid #0369a1;
  padding: 0.875rem 1rem;
  border-radius: 0 0.5rem 0.5rem 0;
}

.help-dialog__purpose {
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.5;
  color: #334155;
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
  color: #475569;
}

.help-dialog__section-title--tips {
  color: #b45309;
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
  background-color: #ffffff;
  border: 1px solid #f1f5f9;
  border-radius: 0.5rem;
  transition: border-color 0.15s ease;
}

.help-steps-item:hover {
  border-color: #cbd5e1;
}

.help-steps-item__num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 1.625rem;
  block-size: 1.625rem;
  border-radius: 50%;
  background-color: #0369a1;
  color: #ffffff;
  font-size: 0.8125rem;
  font-weight: 700;
  flex-shrink: 0;
}

.help-steps-item__text {
  font-size: 0.9rem;
  line-height: 1.45;
  color: #1e293b;
  max-inline-size: 65ch;
  text-wrap: pretty;
}

.help-dialog__section--tips {
  background-color: #fffbeb;
  border: 1px solid #fef3c7;
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
  color: #92400e;
  max-inline-size: 65ch;
  text-wrap: pretty;
}

.help-dialog__footer {
  display: flex;
  justify-content: flex-end;
  padding: clamp(0.75rem, 2cqi, 1rem) clamp(1rem, 2.5cqi, 1.5rem);
  background-color: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.help-dialog__action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  border-radius: 0.5rem;
  border: none;
  background-color: #0369a1;
  color: #ffffff;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.help-dialog__action-btn:hover {
  background-color: #075985;
}

@media (pointer: coarse) {
  .help-dialog__close-btn {
    inline-size: 2.75rem;
    block-size: 2.75rem;
  }
  .help-dialog__action-btn {
    min-block-size: 2.75rem;
    padding: 0.625rem 1.5rem;
  }
}
</style>
