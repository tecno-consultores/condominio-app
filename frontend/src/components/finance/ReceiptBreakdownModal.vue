<script setup lang="ts">
import type { ReciboDesgloseDTO } from '../../stores/financeStore';

defineProps<{
  open: boolean;
  desglose: ReciboDesgloseDTO | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();
</script>

<template>
  <dialog
    v-if="open && desglose"
    id="modal-recibo-desglose"
    open
    class="breakdown-modal"
    aria-labelledby="breakdown-modal-title"
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
.breakdown-modal {
  position: fixed;
  inset: 0;
  inline-size: 100%;
  block-size: 100%;
  background-color: rgba(15, 23, 42, 0.65);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem;
  z-index: 60;
  overscroll-behavior: contain;
}

.breakdown-modal::backdrop {
  background-color: rgba(15, 23, 42, 0.65);
  overscroll-behavior: contain;
}

.breakdown-modal__card {
  inline-size: min(100% - 1rem, 34rem);
  max-block-size: min(85dvh, 40rem);
  overflow-y: auto;
  overscroll-behavior: contain;
  background-color: #ffffff;
  border-radius: 1rem;
  padding: clamp(1rem, 3cqi, 1.5rem);
  border: 1px solid #cbd5e1;
  box-shadow:
    0 20px 25px -5px rgba(15, 23, 42, 0.18),
    0 8px 10px -6px rgba(15, 23, 42, 0.1);
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
  color: #0f172a;
  text-wrap: balance;
}

.breakdown-modal__meta {
  margin: 0.25rem 0 0;
  font-size: 0.825rem;
  color: #475569;
}

.breakdown-modal__badge {
  font-size: 0.725rem;
  font-weight: 700;
  padding: 0.25rem 0.6rem;
  border-radius: 9999px;
  background-color: #e0f2fe;
  color: #0369a1;
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
  border-radius: 0.625rem;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
}

.breakdown-modal__item--credit {
  background-color: #ecfdf5;
  border-color: #a7f3d0;
}

.breakdown-modal__item-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.breakdown-modal__item-type {
  font-size: 0.7rem;
  font-weight: 700;
  color: #64748b;
}

.breakdown-modal__item-desc {
  font-size: 0.85rem;
  color: #0f172a;
}

.breakdown-modal__item-amount {
  font-size: 0.875rem;
  color: #0f172a;
}

.breakdown-modal__summary {
  border-top: 1px solid #e2e8f0;
  padding-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.breakdown-modal__row {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  color: #334155;
}

.breakdown-modal__close {
  margin-top: 0.5rem;
  align-self: flex-end;
  padding: 0.55rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  background-color: #0f172a;
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
</style>
