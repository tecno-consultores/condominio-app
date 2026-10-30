<script setup lang="ts">
import { ref } from 'vue';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import { useFinanceStore, type MonedaPago } from '../../stores/financeStore';

const financeStore = useFinanceStore();

const tasaInput = ref(financeStore.activeRateValue);
const egresoPeriodo = ref('2026-10');
const egresoCategoria = ref('Bombas de Agua');
const egresoDescripcion = ref('');
const egresoMonto = ref('');
const egresoMoneda = ref<MonedaPago>('USD');

const cierrePeriodo = ref('2026-10');
const confirmModalOpen = ref(false);
const dialogRef = ref<HTMLDialogElement | null>(null);
const statusBanner = ref<string | null>(null);

async function saveTasa(): Promise<void> {
  statusBanner.value = null;
  try {
    const saved = await financeStore.registrarTasa(String(tasaInput.value));
    statusBanner.value = `Tasa BCV actualizada a ${saved.tasa_usd_ves} VES/USD.`;
  } catch {
    // Error gestionado en financeStore.errorMessage
  }
}

async function saveEgreso(): Promise<void> {
  statusBanner.value = null;
  try {
    const created = await financeStore.registrarEgreso({
      periodo: egresoPeriodo.value,
      categoria: egresoCategoria.value,
      descripcion: egresoDescripcion.value.trim(),
      monto: String(egresoMonto.value),
      moneda: egresoMoneda.value,
    });
    statusBanner.value = `Egreso #${created.id} registrado (${created.monto_usd} USD).`;
    egresoDescripcion.value = '';
    egresoMonto.value = '';
  } catch {
    // Error gestionado en financeStore.errorMessage
  }
}

function openClosingModal(): void {
  confirmModalOpen.value = true;
}

function closeClosingModal(): void {
  confirmModalOpen.value = false;
}

async function confirmMonthlyClosing(): Promise<void> {
  statusBanner.value = null;
  try {
    const cierre = await financeStore.ejecutarCierreMensual(cierrePeriodo.value);
    closeClosingModal();
    statusBanner.value = `Candado Contable activado para el periodo ${cierre.periodo} (${cierre.estado}).`;
  } catch {
    closeClosingModal();
  }
}
</script>

<template>
  <AppShellLayout>
    <header class="page-header">
      <h1 class="page-header__title">Tesorería: Tasa BCV, Egresos y Candado Contable</h1>
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
          permanentemente (`bloqueado = true`) contra ediciones o nuevos abonos.
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
      :open="confirmModalOpen ? true : undefined"
      aria-labelledby="closing-modal-title"
      class="closing-dialog"
      @close="closeClosingModal"
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
  </AppShellLayout>
</template>

<style scoped>
/* MANDATORY (both rules): without them, scrolling over the backdrop or inside the dialog scrolls the page behind it */
dialog:modal {
  overscroll-behavior: contain;
}

dialog::backdrop {
  overflow: hidden;
  overscroll-behavior: contain;
  background-color: rgba(15, 23, 42, 0.55);
}

.page-header {
  margin-bottom: 1.25rem;
}

.page-header__title {
  margin: 0;
  font-size: 1.3rem;
  color: #0f172a;
}

.page-header__subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: #475569;
}

.banner {
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.banner--error {
  background-color: #fef2f2;
  border: 1px solid #f87171;
  color: #991b1b;
}

.banner--success {
  background-color: #f0fdf4;
  border: 1px solid #4ade80;
  color: #166534;
}

.treasury-grid {
  display: grid;
  gap: 1.25rem;
}

.panel-card {
  padding: 1.25rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
}

.panel-card--warning {
  border-color: #f59e0b;
  background-color: #fffbeb;
}

.panel-card__title {
  margin: 0 0 0.75rem;
  font-size: 1.05rem;
  color: #0f172a;
}

.panel-card__desc {
  margin: 0 0 0.75rem;
  font-size: 0.85rem;
  color: #78350f;
}

.panel-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #1e293b;
}

.field-input {
  min-height: 44px;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  font-size: 0.95rem;
}

.inline-row {
  display: flex;
  gap: 0.75rem;
}

.inline-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.btn-primary {
  min-height: 44px;
  margin-top: 0.5rem;
  padding: 0.625rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background-color: #0284c7;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.btn-danger {
  min-height: 44px;
  margin-top: 0.5rem;
  padding: 0.625rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background-color: #dc2626;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.btn-secondary {
  min-height: 44px;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  background-color: #f8fafc;
  color: #0f172a;
  font-weight: 600;
  cursor: pointer;
}

.closing-dialog[open] {
  display: block;
  width: min(100% - 2rem, 460px);
  border: 1px solid #cbd5e1;
  border-radius: 0.75rem;
  padding: 1.25rem;
  background-color: #ffffff;
  color: #0f172a;
}

.closing-dialog__title {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
}

.closing-dialog__text {
  margin: 0 0 1rem;
  font-size: 0.9rem;
  color: #334155;
}

.closing-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}
</style>
