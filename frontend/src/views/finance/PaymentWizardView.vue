<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import { useIdempotency } from '../../composables/useIdempotency';
import {
  convertUsdToVes,
  convertVesToUsd,
  determinePaymentCoverage,
  useFinanceStore,
  type MetodoPago,
  type MonedaPago,
} from '../../stores/financeStore';
import { validateProofFileUpload } from '../../utils/security';

const financeStore = useFinanceStore();
const router = useRouter();
const { currentKey, isSubmitting, executeWithIdempotency } = useIdempotency();

const currentStep = ref<1 | 2 | 3>(1);
const reciboId = ref(1);
const saldoReciboUsd = ref(50);
const moneda = ref<MonedaPago>('VES');
const monto = ref('1825.00');
const metodoPago = ref<MetodoPago>('PAGO_MOVIL');
const numeroReferencia = ref('');
const urlComprobante = ref('');
const selectedFileName = ref<string | null>(null);
const validationError = ref<string | null>(null);
const successBanner = ref<string | null>(null);

const requiresReference = computed(() => metodoPago.value !== 'EFECTIVO');

const equivalentUsd = computed(() => {
  const rawMonto = String(monto.value);
  if (moneda.value === 'USD') {
    const parsed = Number.parseFloat(rawMonto);
    return Number.isFinite(parsed) && parsed > 0 ? parsed.toFixed(2) : '0.00';
  }
  return convertVesToUsd(rawMonto, financeStore.activeRateValue);
});

const equivalentVes = computed(() => {
  const rawMonto = String(monto.value);
  if (moneda.value === 'VES') {
    const parsed = Number.parseFloat(rawMonto);
    return Number.isFinite(parsed) && parsed > 0 ? parsed.toFixed(2) : '0.00';
  }
  return convertUsdToVes(rawMonto, financeStore.activeRateValue);
});

const coverageType = computed(() =>
  determinePaymentCoverage(Number.parseFloat(equivalentUsd.value) || 0, saldoReciboUsd.value),
);

function goToStep2(): void {
  validationError.value = null;
  const numericAmount = Number.parseFloat(String(monto.value));
  if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
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
    selectedFileName.value = null;
    return;
  }
  const check = validateProofFileUpload({ name: file.name, size: file.size, type: file.type });
  if (!check.valid) {
    validationError.value = check.error ?? 'Archivo inválido.';
    selectedFileName.value = null;
    input.value = '';
    return;
  }
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
  try {
    await executeWithIdempotency(async (key) => {
      await financeStore.reportarPago(
        {
          recibo_id: reciboId.value,
          monto: String(monto.value),
          moneda: moneda.value,
          metodo_pago: metodoPago.value,
          numero_referencia: requiresReference.value ? numeroReferencia.value.trim() : null,
          url_comprobante: urlComprobante.value.trim() || null,
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
  <AppShellLayout>
    <section class="wizard-card" aria-labelledby="wizard-title">
      <header class="wizard-card__header">
        <h1 id="wizard-title" class="wizard-card__title">Reportar Pago de Condominio</h1>
        <span class="wizard-card__step-indicator">Paso {{ currentStep }} de 3</span>
      </header>

      <div v-if="validationError" class="banner banner--error" role="alert">
        {{ validationError }}
      </div>
      <div v-if="successBanner" class="banner banner--success" role="status">
        {{ successBanner }}
      </div>

      <!-- PASO 1: Monto, Moneda y Cobertura -->
      <div v-if="currentStep === 1" class="wizard-step">
        <div class="field-group">
          <label for="select-recibo" class="field-label">Recibo a abonar</label>
          <select id="select-recibo" v-model.number="reciboId" class="field-input">
            <option :value="1">Recibo #1 — Octubre 2026 (Saldo: {{ saldoReciboUsd }} USD)</option>
          </select>
        </div>

        <div class="field-group">
          <label for="select-moneda" class="field-label">Moneda del pago</label>
          <select id="select-moneda" v-model="moneda" class="field-input">
            <option value="VES">
              Bolívares (VES — Tasa BCV {{ financeStore.activeRateValue }})
            </option>
            <option value="USD">Dólares (USD)</option>
          </select>
        </div>

        <div class="field-group">
          <label for="step-1-monto" class="field-label">Monto exacto pagado</label>
          <p id="monto-hint" class="field-hint">
            Equivalente calculado: <strong>{{ equivalentUsd }} USD</strong> ({{ equivalentVes }}
            VES)
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
      <div v-else-if="currentStep === 2" class="wizard-step">
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
      <div v-else class="wizard-step">
        <dl class="summary-list">
          <div class="summary-list__row">
            <dt>Recibo:</dt>
            <dd>#{{ reciboId }}</dd>
          </div>
          <div class="summary-list__row">
            <dt>Monto reportado:</dt>
            <dd>{{ monto }} {{ moneda }} ({{ equivalentUsd }} USD)</dd>
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
            <dt>Llave de Idempotencia:</dt>
            <dd id="idempotency-key-preview">{{ currentKey }}</dd>
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
    </section>
  </AppShellLayout>
</template>

<style scoped>
.wizard-card {
  max-width: 560px;
  margin: 0 auto;
  padding: 1.5rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
}

.wizard-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}

.wizard-card__title {
  margin: 0;
  font-size: 1.2rem;
  color: #0f172a;
}

.wizard-card__step-indicator {
  padding: 0.25rem 0.65rem;
  border-radius: 9999px;
  background-color: #e0f2fe;
  color: #0369a1;
  font-size: 0.8rem;
  font-weight: 700;
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

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 1rem;
}

.field-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #1e293b;
}

.field-hint {
  margin: 0;
  font-size: 0.775rem;
  color: #475569;
}

.field-input {
  min-height: 44px;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  font-size: 0.95rem;
}

.coverage-badge {
  padding: 0.75rem;
  border-radius: 0.5rem;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.summary-list {
  margin: 0 0 1.25rem;
  padding: 0;
}

.summary-list__row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.875rem;
}

.wizard-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-primary {
  min-height: 44px;
  padding: 0.625rem 1.25rem;
  border-radius: 0.5rem;
  border: none;
  background-color: #0284c7;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.btn-secondary {
  min-height: 44px;
  padding: 0.625rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  background-color: #f8fafc;
  color: #0f172a;
  font-weight: 600;
  cursor: pointer;
}
</style>
