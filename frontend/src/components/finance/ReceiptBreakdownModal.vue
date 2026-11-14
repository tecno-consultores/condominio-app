<script setup lang="ts">
import { nextTick, ref, watch } from 'vue';
import type { ReciboDesgloseDTO } from '../../stores/financeStore';

const props = defineProps<{
  open: boolean;
  desglose: ReciboDesgloseDTO | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const dialogRef = ref<HTMLDialogElement | null>(null);

watch(
  () => Boolean(props.open && props.desglose),
  async (isOpen) => {
    if (!isOpen) {
      const el = dialogRef.value;
      if (el?.open && typeof el.close === 'function') {
        el.close();
      }
      return;
    }
    await nextTick();
    const el = dialogRef.value;
    if (el && typeof el.showModal === 'function' && !el.open) {
      el.showModal();
    }
  },
  { immediate: true },
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
</script>

<template>
  <dialog
    v-if="open && desglose"
    id="modal-recibo-desglose"
    ref="dialogRef"
    v-bind="{ closedby: 'any' }"
    class="breakdown-modal top-layer-dialog"
    aria-labelledby="breakdown-modal-title"
    @close="emit('close')"
    @pointerdown="handlePointerDown"
    @pointerup="handlePointerUp"
    @click="handleBackdropClick"
  >
    <div class="breakdown-modal__card">
      <header class="breakdown-modal__header">
        <div>
          <h2 id="breakdown-modal-title" class="breakdown-modal__title">
            Desglose del Recibo #{{ desglose.recibo_id }} — {{ desglose.identificador_unidad }}
          </h2>
          <p class="breakdown-modal__meta">
            Periodo: <strong>{{ desglose.periodo }}</strong> · Alícuota:
            <strong class="tabular-num">{{ desglose.alicuota_aplicada }}%</strong>
          </p>
        </div>
        <span class="breakdown-modal__badge">{{ desglose.estado }}</span>
      </header>

      <ul id="breakdown-items-list" class="breakdown-modal__list" aria-label="Conceptos del recibo">
        <li
          v-for="item in desglose.items"
          :key="item.id"
          class="breakdown-modal__item"
          :class="{ 'breakdown-modal__item--credit': item.tipo_item === 'ABONO_CREDITO_PREVIO' }"
        >
          <div class="breakdown-modal__item-info">
            <span class="breakdown-modal__item-type">{{ item.tipo_item }}</span>
            <span class="breakdown-modal__item-desc">{{ item.descripcion }}</span>
          </div>
          <strong class="breakdown-modal__item-amount tabular-num">
            ${{ item.monto_usd }} USD
          </strong>
        </li>
      </ul>

      <footer class="breakdown-modal__summary">
        <div class="breakdown-modal__row">
          <span>Total Recibo:</span>
          <strong class="tabular-num">${{ desglose.monto_usd }} USD</strong>
        </div>
        <div class="breakdown-modal__row">
          <span>Crédito Descontado:</span>
          <strong class="tabular-num">-${{ desglose.credito_descontado_usd }} USD</strong>
        </div>
        <div class="breakdown-modal__row">
          <span>Saldo Pendiente:</span>
          <strong id="breakdown-saldo-pendiente" class="tabular-num">
            ${{ desglose.saldo_pendiente_usd }} USD
          </strong>
        </div>

        <button
          id="btn-close-desglose"
          type="button"
          autofocus
          class="breakdown-modal__close"
          @click="emit('close')"
        >
          Cerrar Desglose
        </button>
      </footer>
    </div>
  </dialog>
</template>

<style scoped>
dialog:modal {
  overscroll-behavior: contain;
}

.breakdown-modal[open] {
  padding: 0;
  border: none;
  background: transparent;
  inline-size: min(100% - 1.5rem, 34rem);
  max-block-size: min(85dvh, 40rem);
  overscroll-behavior: contain;
}

.breakdown-modal::backdrop {
  overflow: hidden;
  background-color: rgba(15, 23, 42, 0.65);
  overscroll-behavior: contain;
}

.breakdown-modal__card {
  inline-size: 100%;
  max-block-size: min(85dvh, 40rem);
  overflow-y: auto;
  overscroll-behavior: contain;
  background-color: var(--surface-elevated, #ffffff);
  color: var(--text-primary, #0f172a);
  border-radius: var(--radius-lg, 1rem);
  padding: clamp(1rem, 3cqi, 1.5rem);
  border: 1px solid var(--border-subtle, #cbd5e1);
  box-shadow: var(--shadow-modal);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.breakdown-modal__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.breakdown-modal__title {
  margin: 0;
  font-size: clamp(1rem, 2.5cqi, 1.15rem);
  font-weight: 800;
  color: var(--text-primary, #0f172a);
  text-wrap: balance;
}

.breakdown-modal__meta {
  margin: 0.25rem 0 0;
  font-size: 0.825rem;
  color: var(--text-secondary, #475569);
}

.breakdown-modal__badge {
  font-size: 0.725rem;
  font-weight: 700;
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-pill, 9999px);
  background-color: var(--brand-tint, #e0f2fe);
  color: var(--brand-accent, #0369a1);
}

.breakdown-modal__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.breakdown-modal__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.65rem 0.75rem;
  border-radius: var(--radius-sm, 0.625rem);
  background-color: var(--surface-subtle, #f8fafc);
  border: 1px solid var(--border-subtle, #e2e8f0);
}

.breakdown-modal__item--credit {
  background-color: var(--status-ok-bg, #ecfdf5);
  border-color: var(--status-ok-border, #a7f3d0);
  color: var(--status-ok-text, #14532d);
}

.breakdown-modal__item-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.breakdown-modal__item-type {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--text-secondary, #64748b);
}

.breakdown-modal__item-desc {
  font-size: 0.85rem;
  color: var(--text-primary, #0f172a);
}

.breakdown-modal__item-amount {
  font-size: 0.875rem;
  color: var(--text-primary, #0f172a);
}

.breakdown-modal__summary {
  border-top: 1px solid var(--border-subtle, #e2e8f0);
  padding-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.breakdown-modal__row {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  color: var(--text-secondary, #334155);
}

.breakdown-modal__close {
  margin-top: 0.5rem;
  align-self: flex-end;
  padding: 0.55rem 1rem;
  border-radius: var(--radius-sm, 0.5rem);
  border: 1px solid var(--brand-600, #0369a1);
  background-color: var(--brand-600, #0369a1);
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.tabular-num {
  font-variant-numeric: tabular-nums;
}

@media (pointer: coarse) {
  .breakdown-modal__close {
    min-block-size: 2.75rem;
  }
}

@media (max-width: 639px) {
  .breakdown-modal[open] {
    margin: auto 0 0 0;
    inline-size: 100%;
    max-inline-size: 100%;
    max-block-size: 88dvh;
    border-radius: var(--radius-lg, 1rem) var(--radius-lg, 1rem) 0 0;
  }

  .breakdown-modal__card {
    border-radius: var(--radius-lg, 1rem) var(--radius-lg, 1rem) 0 0;
    max-block-size: 88dvh;
  }
}
</style>
