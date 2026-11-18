<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import EmptyStateCard from '../../components/common/EmptyStateCard.vue';
import SkeletonCard from '../../components/common/SkeletonCard.vue';
import { useIdempotency } from '../../composables/useIdempotency';
import { useAuthStore } from '../../stores/authStore';
import {
  convertUsdToVes,
  convertVesToUsd,
  determinePaymentCoverage,
  useFinanceStore,
  type EstadoCobranzaItemDTO,
  type MetodoPago,
  type MonedaPago,
} from '../../stores/financeStore';
import { useOperationsStore } from '../../stores/operationsStore';
import { compareDecimal, roundDecimalHalfUp } from '../../utils/decimal';
import { validateProofFileUpload } from '../../utils/security';

const authStore = useAuthStore();
const financeStore = useFinanceStore();
const operationsStore = useOperationsStore();
const router = useRouter();
const { isSubmitting, executeWithIdempotency } = useIdempotency();

const currentStep = ref<1 | 2 | 3>(1);
const reciboId = ref<number | null>(null);
const moneda = ref<MonedaPago>('VES');
const monto = ref('');
const hasEditedMonto = ref(false);
const metodoPago = ref<MetodoPago>('PAGO_MOVIL');
const numeroReferencia = ref('');
const urlComprobante = ref('');
const selectedFile = ref<File | null>(null);
const selectedFileName = ref<string | null>(null);
const validationError = ref<string | null>(null);
const successBanner = ref<string | null>(null);

const requiresReference = computed(() => metodoPago.value !== 'EFECTIVO');
const hasOfficialRate = computed(
  () =>
    financeStore.activeRateValue !== null && compareDecimal(financeStore.activeRateValue, '0') > 0,
);

const unitLabels = computed<Record<number, string>>(() => {
  const labels: Record<number, string> = {};
  for (const unidad of operationsStore.data.unidades) {
    labels[unidad.id] = unidad.identificador;
  }
  return labels;
});

const pendingReceipts = computed<EstadoCobranzaItemDTO[]>(() => {
  const ownUnitId = authStore.activeUnitId;
  const items = (financeStore.data.resumen?.estado_cobranza ?? []).filter(
    (item): item is EstadoCobranzaItemDTO & { recibo_id: number } =>
      typeof item.recibo_id === 'number' && compareDecimal(item.saldo_usd, '0') > 0,
  );
  return [...items].sort((a, b) => {
    if (ownUnitId !== null) {
      if (a.unidad_id === ownUnitId && b.unidad_id !== ownUnitId) return -1;
      if (b.unidad_id === ownUnitId && a.unidad_id !== ownUnitId) return 1;
    }
    return b.periodo.localeCompare(a.periodo) || a.unidad_id - b.unidad_id;
  });
});

const selectedReceipt = computed<EstadoCobranzaItemDTO | null>(
  () =>
    pendingReceipts.value.find((item) => item.recibo_id === reciboId.value) ??
    pendingReceipts.value[0] ??
    null,
);

const saldoReciboUsd = computed(() => selectedReceipt.value?.saldo_usd ?? '0.00');

function formatUnitName(unidadId: number): string {
  return unitLabels.value[unidadId] ?? 'Unidad asignada';
}

function formatReceiptOption(item: EstadoCobranzaItemDTO): string {
  return `${formatUnitName(item.unidad_id)} — Periodo ${item.periodo} (Saldo: ${item.saldo_usd} USD)`;
}

const selectedReceiptLabel = computed(() =>
  selectedReceipt.value ? formatReceiptOption(selectedReceipt.value) : 'Sin recibo seleccionado',
);

function syncDefaultMonto(): void {
  if (hasEditedMonto.value || !selectedReceipt.value) {
    return;
  }
  if (moneda.value === 'USD') {
    monto.value = roundDecimalHalfUp(selectedReceipt.value.saldo_usd, 2);
    return;
  }
  if (hasOfficialRate.value && financeStore.activeRateValue) {
    monto.value = convertUsdToVes(selectedReceipt.value.saldo_usd, financeStore.activeRateValue);
    return;
  }
  moneda.value = 'USD';
  monto.value = roundDecimalHalfUp(selectedReceipt.value.saldo_usd, 2);
}

watch(
  pendingReceipts,
  (list) => {
    if (list.length === 0) {
      reciboId.value = null;
      return;
    }
    if (!list.some((item) => item.recibo_id === reciboId.value)) {
      reciboId.value = list[0]?.recibo_id ?? null;
    }
    syncDefaultMonto();
  },
  { immediate: true },
);

watch(moneda, () => {
  if (!hasEditedMonto.value) {
    syncDefaultMonto();
  }
});

onMounted(async () => {
  await Promise.allSettled([financeStore.fetchDashboardData(), operationsStore.fetchUnidades()]);
  syncDefaultMonto();
});

const equivalentUsd = computed(() => {
  const rawMonto = String(monto.value ?? '').trim();
  if (!rawMonto || compareDecimal(rawMonto, '0') <= 0) {
    return '0.00';
  }
  if (moneda.value === 'USD') {
    return roundDecimalHalfUp(rawMonto, 2);
  }
  if (!hasOfficialRate.value || !financeStore.activeRateValue) {
    return '0.00';
  }
  return convertVesToUsd(rawMonto, financeStore.activeRateValue);
});

const equivalentVes = computed(() => {
  const rawMonto = String(monto.value ?? '').trim();
  if (!rawMonto || compareDecimal(rawMonto, '0') <= 0) {
    return '0.00';
  }
  if (moneda.value === 'VES') {
    return roundDecimalHalfUp(rawMonto, 2);
  }
  if (!hasOfficialRate.value || !financeStore.activeRateValue) {
    return 'Pendiente tasa BCV';
  }
  return convertUsdToVes(rawMonto, financeStore.activeRateValue);
});

const coverageType = computed(() =>
  determinePaymentCoverage(equivalentUsd.value, saldoReciboUsd.value),
);

function onMontoInput(): void {
  hasEditedMonto.value = true;
}

function goToStep2(): void {
  validationError.value = null;
  if (reciboId.value === null) {
    validationError.value = 'No hay un recibo pendiente seleccionado.';
    return;
  }
  const rawMonto = String(monto.value ?? '').trim();
  if (compareDecimal(rawMonto, '0') <= 0) {
    validationError.value = 'El monto a reportar debe ser mayor a cero.';
    return;
  }
  currentStep.value = 2;
}

function handleFileChange(event: Event): void {
  validationError.value = null;
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    selectedFile.value = null;
    selectedFileName.value = null;
    return;
  }
  const check = validateProofFileUpload({ name: file.name, size: file.size, type: file.type });
  if (!check.valid) {
    validationError.value = check.error ?? 'Archivo inválido.';
    selectedFile.value = null;
    selectedFileName.value = null;
    input.value = '';
    return;
  }
  selectedFile.value = file;
  selectedFileName.value = file.name;
}

function goToStep3(): void {
  validationError.value = null;
  if (requiresReference.value && numeroReferencia.value.trim().length < 4) {
    validationError.value =
      'El número de referencia bancaria es obligatorio para transferencias, Pago Móvil y Zelle.';
    return;
  }
  currentStep.value = 3;
}

async function submitPayment(): Promise<void> {
  validationError.value = null;
  if (reciboId.value === null) {
    validationError.value = 'Debes seleccionar un recibo pendiente.';
    return;
  }
  const rawMonto = String(monto.value ?? '').trim();
  if (compareDecimal(rawMonto, '0') <= 0) {
    validationError.value = 'El monto a reportar debe ser mayor a cero.';
    return;
  }

  try {
    await executeWithIdempotency(async (key) => {
      let uploadedUrl: string | null = urlComprobante.value.trim() || null;
      if (selectedFile.value) {
        const uploadResult = await financeStore.subirEvidencia(selectedFile.value, 'comprobantes');
        uploadedUrl = uploadResult.url;
      }
      await financeStore.reportarPago(
        {
          recibo_id: reciboId.value!,
          monto: roundDecimalHalfUp(rawMonto, 2),
          moneda: moneda.value,
          metodo_pago: metodoPago.value,
          numero_referencia: requiresReference.value ? numeroReferencia.value.trim() : null,
          url_comprobante: uploadedUrl,
        },
        key,
      );
    });
    successBanner.value = 'Pago reportado con éxito. En espera de conciliación por Tesorería.';
    await router.push('/dashboard');
  } catch {
    validationError.value =
      financeStore.errorMessage ?? 'Error al procesar el reporte de pago. Intente nuevamente.';
  }
}
</script>

<template>
  <section class="wizard-card" aria-labelledby="wizard-title">
    <header class="wizard-card__header">
      <h1 id="wizard-title" class="wizard-card__title">Reportar Pago de Condominio</h1>
      <span class="wizard-card__step-indicator tabular-nums">Paso {{ currentStep }} de 3</span>
    </header>

    <ol id="wizard-stepper" class="wizard-stepper" aria-label="Progreso de reporte de pago">
      <li
        class="wizard-stepper__item"
        :class="{
          'wizard-stepper__item--active': currentStep === 1,
          'wizard-stepper__item--done': currentStep > 1,
        }"
      >
        1. Monto y Recibo
      </li>
      <li
        class="wizard-stepper__item"
        :class="{
          'wizard-stepper__item--active': currentStep === 2,
          'wizard-stepper__item--done': currentStep > 2,
        }"
      >
        2. Método y Soporte
      </li>
      <li
        class="wizard-stepper__item"
        :class="{ 'wizard-stepper__item--active': currentStep === 3 }"
      >
        3. Confirmar Envío
      </li>
    </ol>

    <div v-if="validationError" class="banner banner--error" role="alert">
      {{ validationError }}
    </div>
    <div v-if="successBanner" class="banner banner--success" role="status">
      {{ successBanner }}
    </div>

    <SkeletonCard
      v-if="financeStore.isLoading && pendingReceipts.length === 0"
      :lines="3"
      height="140px"
      label="Cargando recibos pendientes..."
    />

    <EmptyStateCard
      v-else-if="pendingReceipts.length === 0"
      title="No tienes recibos pendientes por abonar"
      description="Cuando exista un recibo con saldo pendiente aparecerá aquí para reportar tu pago."
    />

    <Transition v-else name="fade-slide">
      <!-- PASO 1: Monto, Moneda y Cobertura -->
      <div v-if="currentStep === 1" key="step-1" class="wizard-step">
        <div class="field-group">
          <label for="select-recibo" class="field-label">Recibo a abonar</label>
          <select id="select-recibo" v-model.number="reciboId" class="field-input">
            <option v-for="item in pendingReceipts" :key="item.recibo_id" :value="item.recibo_id">
              {{ formatReceiptOption(item) }}
            </option>
          </select>
        </div>

        <div class="field-group">
          <label for="select-moneda" class="field-label">Moneda del pago</label>
          <select id="select-moneda" v-model="moneda" class="field-input">
            <option value="VES">
              Bolívares (VES —
              {{
                hasOfficialRate && financeStore.activeRateValue
                  ? `Tasa BCV ${financeStore.activeRateValue}`
                  : 'Tasa BCV pendiente hoy'
              }})
            </option>
            <option value="USD">Dólares (USD)</option>
          </select>
        </div>

        <div class="field-group">
          <label for="step-1-monto" class="field-label">Monto exacto pagado</label>
          <p id="monto-hint" class="field-hint tabular-nums">
            Equivalente calculado: <strong>{{ equivalentUsd }} USD</strong> ({{
              equivalentVes === 'Pendiente tasa BCV' ? equivalentVes : `${equivalentVes} VES`
            }})
          </p>
          <input
            id="step-1-monto"
            v-model="monto"
            type="number"
            step="0.01"
            min="0.01"
            required
            aria-describedby="monto-hint"
            class="field-input"
            @input="onMontoInput"
          />
        </div>

        <div id="badge-tipo-cobertura" class="coverage-badge">
          Modalidad detectada:
          <strong>{{ coverageType === 'PAGO_TOTAL' ? 'PAGO TOTAL' : 'ABONO PARCIAL' }}</strong>
        </div>

        <div class="wizard-actions">
          <button id="btn-step-1-next" type="button" class="btn-primary" @click="goToStep2">
            Continuar al Paso 2
          </button>
        </div>
      </div>

      <!-- PASO 2: Método, Referencia y Comprobante (<= 2 MB) -->
      <div v-else-if="currentStep === 2" key="step-2" class="wizard-step">
        <div class="field-group">
          <label for="step-2-metodo" class="field-label">Método de pago utilizado</label>
          <select id="step-2-metodo" v-model="metodoPago" class="field-input">
            <option value="PAGO_MOVIL">Pago Móvil</option>
            <option value="TRANSFERENCIA">Transferencia Bancaria</option>
            <option value="ZELLE">Zelle (USD)</option>
            <option value="EFECTIVO">Efectivo en Taquilla</option>
          </select>
        </div>

        <div v-if="requiresReference" class="field-group">
          <label for="input-referencia" class="field-label">Número de referencia bancaria</label>
          <p id="referencia-hint" class="field-hint">
            Ingresa los últimos dígitos o código de confirmación (mínimo 4 caracteres).
          </p>
          <input
            id="input-referencia"
            v-model="numeroReferencia"
            type="text"
            required
            minlength="4"
            aria-describedby="referencia-hint"
            class="field-input"
          />
        </div>

        <div class="field-group">
          <label for="step-3-comprobante" class="field-label">
            Comprobante digital (JPG, PNG, WEBP, AVIF o PDF — máx. 2 MB)
          </label>
          <input
            id="step-3-comprobante"
            type="file"
            accept="image/jpeg,image/png,image/webp,image/avif,application/pdf"
            class="field-input"
            @change="handleFileChange"
          />
          <p v-if="selectedFileName" class="field-hint">Archivo validado: {{ selectedFileName }}</p>
        </div>

        <div class="wizard-actions">
          <button id="btn-step-2-back" type="button" class="btn-secondary" @click="currentStep = 1">
            Atrás
          </button>
          <button id="btn-step-2-next" type="button" class="btn-primary" @click="goToStep3">
            Revisar y Confirmar
          </button>
        </div>
      </div>

      <!-- PASO 3: Resumen Inmutable y Envío Idempotente -->
      <div v-else key="step-3" class="wizard-step">
        <dl class="summary-list">
          <div class="summary-list__row">
            <dt>Recibo:</dt>
            <dd>{{ selectedReceiptLabel }}</dd>
          </div>
          <div class="summary-list__row">
            <dt>Monto reportado:</dt>
            <dd class="tabular-nums">{{ monto }} {{ moneda }} ({{ equivalentUsd }} USD)</dd>
          </div>
          <div class="summary-list__row">
            <dt>Cobertura:</dt>
            <dd>{{ coverageType }}</dd>
          </div>
          <div class="summary-list__row">
            <dt>Método y Referencia:</dt>
            <dd>
              {{ metodoPago }} — {{ requiresReference ? numeroReferencia : 'N/A (Efectivo)' }}
            </dd>
          </div>
          <div class="summary-list__row">
            <dt>Protección de envío:</dt>
            <dd id="idempotency-key-preview">Protección anti-duplicado activa</dd>
          </div>
        </dl>

        <div class="wizard-actions">
          <button id="btn-step-3-back" type="button" class="btn-secondary" @click="currentStep = 2">
            Atrás
          </button>
          <button
            id="btn-submit-pago"
            type="button"
            class="btn-primary"
            :disabled="isSubmitting"
            :aria-busy="isSubmitting ? 'true' : 'false'"
            @click="submitPayment"
          >
            {{ isSubmitting ? 'Enviando...' : 'Confirmar y Enviar Pago' }}
          </button>
        </div>
      </div>
    </Transition>
  </section>
</template>

<style scoped>
.wizard-card {
  max-width: 560px;
  margin: 0 auto;
  padding: 1.5rem;
  border-radius: var(--radius-lg);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-card);
}

.wizard-card__header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.wizard-card__title {
  margin: 0;
  font-size: 1.2rem;
  color: var(--text-primary);
}

.wizard-card__step-indicator {
  padding: 0.25rem 0.65rem;
  border-radius: var(--radius-pill);
  background-color: var(--brand-tint);
  color: var(--brand-accent);
  font-size: 0.8rem;
  font-weight: 700;
}

.wizard-stepper {
  list-style: none;
  padding: 0;
  margin: 0 0 1.25rem;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}

.wizard-stepper__item {
  text-align: center;
  padding: 0.4rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
  background-color: var(--surface-subtle);
  border: 1px solid var(--border-subtle);
}

.wizard-stepper__item--active {
  background-color: var(--brand-600);
  border-color: var(--brand-600);
  color: var(--text-on-accent);
}

.wizard-stepper__item--done {
  background-color: var(--status-ok-bg);
  border-color: var(--status-ok-border);
  color: var(--status-ok-text);
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

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 1rem;
}

.field-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

.field-hint {
  margin: 0;
  font-size: 0.775rem;
  color: var(--text-secondary);
}

.field-input {
  min-block-size: 2.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-card);
  color: var(--text-primary);
  font-size: 0.95rem;
}

.coverage-badge {
  padding: 0.75rem;
  border-radius: var(--radius-sm);
  background-color: var(--surface-subtle);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.summary-list {
  margin: 0 0 1.25rem;
  padding: 0;
}

.summary-list__row {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 0.875rem;
  color: var(--text-primary);
}

.wizard-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-primary {
  min-block-size: 2.75rem;
  padding: 0.625rem 1.25rem;
  border-radius: var(--radius-sm);
  border: none;
  background-color: var(--brand-600);
  color: var(--text-on-accent);
  font-weight: 700;
  cursor: pointer;
}

.btn-secondary {
  min-block-size: 2.75rem;
  padding: 0.625rem 1rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-subtle);
  color: var(--text-primary);
  font-weight: 600;
  cursor: pointer;
}
</style>
