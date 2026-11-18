<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { ref } from 'vue';
import { useTopLayerDialog } from '../../composables/useTopLayerDialog';
import { useFinanceStore, type MonedaPago } from '../../stores/financeStore';
import { compareDecimal, roundDecimalHalfUp } from '../../utils/decimal';

const financeStore = useFinanceStore();

const tasaInput = ref(financeStore.activeRateValue ?? '');
const egresoPeriodo = ref('2026-10');
const egresoCategoria = ref('Bombas de Agua');
const egresoDescripcion = ref('');
const egresoMonto = ref('');
const egresoMoneda = ref<MonedaPago>('USD');

const cierrePeriodo = ref('2026-10');
const confirmModalOpen = ref(false);
const dialogRef = ref<HTMLDialogElement | null>(null);
const statusBanner = ref<string | null>(null);
const validationError = ref<string | null>(null);

function closeClosingModal(): void {
  confirmModalOpen.value = false;
}

const { dialogProps, onPointerDown, onPointerUp, onBackdropClick } = useTopLayerDialog({
  dialogRef,
  isOpen: () => confirmModalOpen.value,
  onClose: closeClosingModal,
  unmountsWhenClosed: false,
});

async function saveTasa(): Promise<void> {
  statusBanner.value = null;
  validationError.value = null;
  const rawTasa = String(tasaInput.value ?? '').trim();
  if (!rawTasa || compareDecimal(rawTasa, '0') <= 0) {
    validationError.value = 'La tasa BCV debe ser mayor a cero.';
    return;
  }
  try {
    const saved = await financeStore.registrarTasa(roundDecimalHalfUp(rawTasa, 2));
    statusBanner.value = `Tasa BCV actualizada a ${saved.tasa_usd_ves} VES/USD.`;
  } catch {
    // Error gestionado en financeStore.errorMessage
  }
}

async function saveEgreso(): Promise<void> {
  statusBanner.value = null;
  validationError.value = null;
  const rawMonto = String(egresoMonto.value ?? '').trim();
  if (!rawMonto || compareDecimal(rawMonto, '0') <= 0) {
    validationError.value = 'El monto del egreso debe ser mayor a cero.';
    return;
  }
  try {
    const created = await financeStore.registrarEgreso({
      periodo: egresoPeriodo.value.trim(),
      categoria: egresoCategoria.value,
      descripcion: egresoDescripcion.value.trim(),
      monto: roundDecimalHalfUp(rawMonto, 2),
      moneda: egresoMoneda.value,
    });
    statusBanner.value = `Egreso registrado (${created.monto_usd} USD).`;
    egresoDescripcion.value = '';
    egresoMonto.value = '';
  } catch {
    // Error gestionado en financeStore.errorMessage
  }
}

function openClosingModal(): void {
  confirmModalOpen.value = true;
}

async function confirmMonthlyClosing(): Promise<void> {
  statusBanner.value = null;
  validationError.value = null;
  try {
    const cierre = await financeStore.ejecutarCierreMensual(cierrePeriodo.value.trim());
    closeClosingModal();
    statusBanner.value = `Candado Contable activado para el periodo ${cierre.periodo} (${cierre.estado}).`;
  } catch {
    closeClosingModal();
  }
}
</script>

<template>
  <section aria-labelledby="closing-page-title">
    <header class="page-header">
      <h1 id="closing-page-title" class="page-header__title">
        Tesorería: Tasa BCV, Egresos y Candado Contable
      </h1>
      <p class="page-header__subtitle">
        Administra la tasa oficial del día, registra gastos comunes y ejecuta el cierre mensual
        inmutable.
      </p>
    </header>

    <div
      v-if="financeStore.errorMessage"
      id="closing-conflict-banner"
      class="banner banner--error"
      role="alert"
    >
      {{ financeStore.errorMessage }}
    </div>
    <div v-if="validationError" class="banner banner--error" role="alert">
      {{ validationError }}
    </div>
    <div v-if="statusBanner" class="banner banner--success" role="status">
      {{ statusBanner }}
    </div>

    <div class="treasury-grid">
      <!-- 1. Registro de Tasa BCV -->
      <section class="panel-card" aria-labelledby="tasa-section-title">
        <h2 id="tasa-section-title" class="panel-card__title">1. Tasa Oficial BCV del Día</h2>
        <form class="panel-form" @submit.prevent="saveTasa">
          <label for="input-tasa-bcv" class="field-label">Tasa VES / USD</label>
          <input
            id="input-tasa-bcv"
            v-model="tasaInput"
            type="number"
            step="0.01"
            min="0.01"
            required
            class="field-input"
          />
          <button id="btn-save-tasa" type="submit" class="btn-primary">Guardar Tasa BCV</button>
        </form>
      </section>

      <!-- 2. Registro de Egresos -->
      <section class="panel-card" aria-labelledby="egreso-section-title">
        <h2 id="egreso-section-title" class="panel-card__title">2. Registrar Gasto / Egreso</h2>
        <form class="panel-form" @submit.prevent="saveEgreso">
          <label for="input-egreso-periodo" class="field-label">Periodo (YYYY-MM)</label>
          <input
            id="input-egreso-periodo"
            v-model="egresoPeriodo"
            type="text"
            required
            class="field-input"
          />

          <label for="select-egreso-categoria" class="field-label">Categoría</label>
          <select id="select-egreso-categoria" v-model="egresoCategoria" class="field-input">
            <option value="Bombas de Agua">Bombas de Agua</option>
            <option value="Ascensores">Ascensores</option>
            <option value="Vigilancia">Vigilancia</option>
            <option value="Jardinería">Jardinería</option>
          </select>

          <label for="input-egreso-descripcion" class="field-label">Descripción del servicio</label>
          <input
            id="input-egreso-descripcion"
            v-model="egresoDescripcion"
            type="text"
            required
            class="field-input"
          />

          <div class="inline-row">
            <div class="inline-col">
              <label for="input-egreso-monto" class="field-label">Monto</label>
              <input
                id="input-egreso-monto"
                v-model="egresoMonto"
                type="number"
                step="0.01"
                min="0.01"
                required
                class="field-input"
              />
            </div>
            <div class="inline-col">
              <label for="select-egreso-moneda" class="field-label">Moneda</label>
              <select id="select-egreso-moneda" v-model="egresoMoneda" class="field-input">
                <option value="USD">USD</option>
                <option value="VES">VES</option>
              </select>
            </div>
          </div>

          <button id="btn-save-egreso" type="submit" class="btn-primary">Registrar Egreso</button>
        </form>
      </section>

      <!-- 3. Candado Contable (Cierre Mensual Inmutable) -->
      <section class="panel-card panel-card--warning" aria-labelledby="candado-section-title">
        <h2 id="candado-section-title" class="panel-card__title">
          3. Candado Contable (Cierre Mensual Inmutable)
        </h2>
        <p class="panel-card__desc">
          Al cerrar el periodo, todos los recibos y egresos del mes quedan bloqueados
          permanentemente (<code>bloqueado = true</code>) contra ediciones o nuevos abonos.
        </p>
        <div class="panel-form">
          <label for="input-cierre-periodo" class="field-label">Periodo a cerrar</label>
          <input
            id="input-cierre-periodo"
            v-model="cierrePeriodo"
            type="text"
            class="field-input"
          />
          <button
            id="btn-open-closing-modal"
            type="button"
            class="btn-danger"
            @click="openClosingModal"
          >
            Ejecutar Candado Contable
          </button>
        </div>
      </section>
    </div>

    <!-- MANDATORY: no role="dialog" or aria-modal; the native modal already provides them -->
    <dialog
      id="modal-confirm-closing"
      ref="dialogRef"
      v-bind="dialogProps"
      aria-labelledby="closing-modal-title"
      class="closing-dialog top-layer-dialog"
      @cancel.prevent="closeClosingModal"
      @close="closeClosingModal"
      @pointerdown="onPointerDown"
      @pointerup="onPointerUp"
      @click="onBackdropClick"
    >
      <h2 id="closing-modal-title" class="closing-dialog__title">
        ¿Confirmar Candado Contable para {{ cierrePeriodo }}?
      </h2>
      <p class="closing-dialog__text">
        Esta operación es <strong>irreversible</strong>. Una vez cerrado el mes {{ cierrePeriodo }},
        ningún recibo ni egreso de este periodo podrá ser modificado.
      </p>
      <div class="closing-dialog__actions">
        <button
          id="btn-cancel-closing"
          type="button"
          autofocus
          class="btn-secondary"
          @click="closeClosingModal"
        >
          Cancelar
        </button>
        <button
          id="btn-confirm-closing"
          type="button"
          class="btn-danger"
          @click="confirmMonthlyClosing"
        >
          Sí, Cerrar Mes Permanentemente
        </button>
      </div>
    </dialog>
  </section>
</template>

<style scoped>
.page-header {
  margin-bottom: 1.25rem;
}

.page-header__title {
  margin: 0;
  font-size: 1.3rem;
  color: var(--text-primary);
}

.page-header__subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.banner {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-sm);
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.banner--error {
  background-color: var(--status-danger-bg);
  border: 1px solid var(--status-danger-border);
  color: var(--status-danger-text);
}

.banner--success {
  background-color: var(--status-ok-bg);
  border: 1px solid var(--status-ok-border);
  color: var(--status-ok-text);
}

.treasury-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
  gap: 1.25rem;
  align-items: start;
}

.panel-card {
  padding: clamp(1rem, 2.5cqi, 1.5rem);
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-card);
}

.panel-card--warning {
  border-color: var(--status-warn-border);
  background-color: var(--status-warn-bg);
  color: var(--status-warn-text);
}

.panel-card__title {
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
  text-wrap: balance;
  color: var(--text-primary);
}

.panel-card--warning .panel-card__title,
.panel-card--warning .panel-card__desc {
  color: var(--status-warn-text);
}

.panel-card__desc {
  margin: 0 0 0.75rem;
  max-inline-size: 65ch;
  text-wrap: pretty;
  font-size: 0.85rem;
}

.panel-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
}

.field-input {
  min-block-size: 2.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-card);
  color: var(--text-primary);
  font-size: 0.95rem;
  font-variant-numeric: tabular-nums;
}

.inline-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.inline-col {
  flex: 1 1 8rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.btn-primary,
.btn-danger,
.btn-secondary {
  min-block-size: 2.75rem;
  padding: 0.625rem 1rem;
  border-radius: var(--radius-sm);
  font-weight: 700;
  cursor: pointer;
}

.btn-primary {
  margin-top: 0.5rem;
  border: none;
  background-color: var(--brand-600);
  color: var(--text-on-accent);
}

.btn-danger {
  margin-top: 0.5rem;
  border: 1px solid var(--status-danger-border);
  background-color: var(--status-danger-bg);
  color: var(--status-danger-text);
}

.btn-secondary {
  border: 1px solid var(--border-control);
  background-color: var(--surface-subtle);
  color: var(--text-primary);
  font-weight: 600;
}

.closing-dialog[open] {
  display: block;
  inline-size: min(100% - 1.5rem, 28.75rem);
  max-block-size: min(85dvh, 38rem);
  overflow-y: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: clamp(1rem, 3vw, 1.5rem);
  background-color: var(--surface-elevated);
  color: var(--text-primary);
  box-shadow: var(--shadow-modal);
}

.closing-dialog__title {
  margin: 0 0 0.5rem;
  font-size: clamp(1rem, 2.5vw, 1.15rem);
  text-wrap: balance;
}

.closing-dialog__text {
  margin: 0 0 1rem;
  max-inline-size: 65ch;
  text-wrap: pretty;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.closing-dialog__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.75rem;
}
</style>
