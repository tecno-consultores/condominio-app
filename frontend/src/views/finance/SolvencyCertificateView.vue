<script setup lang="ts">
import { onMounted, ref } from 'vue';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import { useIdempotency } from '../../composables/useIdempotency';
import { useFinanceStore } from '../../stores/financeStore';
import { useOperationsStore } from '../../stores/operationsStore';

const financeStore = useFinanceStore();
const operationsStore = useOperationsStore();
const { currentKey, rotateKey } = useIdempotency();

const selectedUnidadId = ref(1);
const verifyFolio = ref('');
const verifySig = ref('');
const validationError = ref<string | null>(null);
const successBanner = ref<string | null>(null);

onMounted(() => {
  void operationsStore.fetchAdminData();
});

async function handleEmitSolvency(): Promise<void> {
  validationError.value = null;
  successBanner.value = null;

  try {
    const cert = await financeStore.emitirCertificadoSolvencia(
      selectedUnidadId.value,
      currentKey.value,
    );
    rotateKey();
    verifyFolio.value = cert.folio;
    verifySig.value = cert.firma_hmac;
    successBanner.value = `Certificado ${cert.folio} emitido para ${cert.identificador_unidad}.`;
  } catch {
    // Error preservado en financeStore.errorMessage
  }
}

async function handleVerifySolvency(): Promise<void> {
  validationError.value = null;
  successBanner.value = null;

  if (verifyFolio.value.trim().length < 4 || verifySig.value.trim().length < 8) {
    validationError.value = 'Indique el folio y la firma criptográfica HMAC-SHA256 a verificar.';
    return;
  }

  try {
    await financeStore.verificarCertificadoSolvencia(verifyFolio.value, verifySig.value);
  } catch {
    // Error preservado en financeStore.errorMessage
  }
}
</script>

<template>
  <AppShellLayout>
    <section class="solvency-view" aria-labelledby="solvency-view-heading">
      <header class="solvency-view__header">
        <h1 id="solvency-view-heading" class="solvency-view__title">
          Certificado Digital de Solvencia (Art. 14 LPH)
        </h1>
        <p class="solvency-view__subtitle">
          Emita y verifique certificados inmutables con sello criptográfico HMAC-SHA256 para
          unidades con deuda cero ($0.00 USD).
        </p>
      </header>

      <div
        v-if="financeStore.errorMessage"
        id="solvencia-error-banner"
        class="solvency-view__alert solvency-view__alert--warning"
        role="status"
      >
        {{ financeStore.errorMessage }}
      </div>

      <div
        v-if="successBanner"
        id="solvencia-success-banner"
        class="solvency-view__alert solvency-view__alert--success"
        role="status"
      >
        {{ successBanner }}
      </div>

      <p v-if="validationError" id="solvencia-validation-error" class="solvency-view__error">
        {{ validationError }}
      </p>

      <div class="solvency-view__layout">
        <article id="card-solvencia-status" class="solvency-view__card">
          <h2 class="solvency-view__card-title">Emisión de Certificado de Solvencia</h2>

          <div class="solvency-view__field">
            <label for="input-solvencia-unidad-id" class="solvency-view__label">
              Unidad Habitacional
            </label>
            <select
              id="input-solvencia-unidad-id"
              v-model.number="selectedUnidadId"
              class="solvency-view__input"
            >
              <option v-for="u in operationsStore.data.unidades" :key="u.id" :value="u.id">
                #{{ u.id }} — {{ u.identificador }}
              </option>
            </select>
          </div>

          <button
            id="btn-emitir-solvencia"
            type="button"
            class="solvency-view__submit"
            @click="handleEmitSolvency"
          >
            Emitir Certificado de Solvencia
          </button>

          <div
            v-if="financeStore.data.certificadoSolvenciaActivo"
            id="qr-solvencia-badge"
            class="solvency-view__certificate"
          >
            <div class="solvency-view__cert-row">
              <span>Folio Oficial:</span>
              <strong>{{ financeStore.data.certificadoSolvenciaActivo.folio }}</strong>
            </div>
            <div class="solvency-view__cert-row">
              <span>Unidad:</span>
              <strong>{{
                financeStore.data.certificadoSolvenciaActivo.identificador_unidad
              }}</strong>
            </div>
            <div class="solvency-view__cert-row">
              <span>Deuda Verificada:</span>
              <strong class="tabular-num">
                ${{ financeStore.data.certificadoSolvenciaActivo.deuda_verificada_usd }} USD
              </strong>
            </div>
            <div class="solvency-view__cert-row">
              <span>Vigencia Hasta:</span>
              <strong>{{ financeStore.data.certificadoSolvenciaActivo.fecha_vencimiento }}</strong>
            </div>
            <div class="solvency-view__qr-box">
              <span class="solvency-view__qr-label">Sello QR HMAC-SHA256</span>
              <code class="solvency-view__qr-code">
                {{ financeStore.data.certificadoSolvenciaActivo.qr_token }}
              </code>
            </div>
          </div>
        </article>

        <form
          id="form-verificar-solvencia"
          class="solvency-view__card"
          novalidate
          @submit.prevent="handleVerifySolvency"
        >
          <h2 class="solvency-view__card-title">Verificación Pública de Autenticidad</h2>

          <div class="solvency-view__field">
            <label for="input-verificar-folio" class="solvency-view__label"
              >Folio del Certificado</label
            >
            <input
              id="input-verificar-folio"
              v-model="verifyFolio"
              type="text"
              class="solvency-view__input"
              placeholder="Ej. SOLV-202610-0001-ABCD"
            />
          </div>

          <div class="solvency-view__field">
            <label for="input-verificar-sig" class="solvency-view__label"
              >Firma Criptográfica (HMAC-SHA256)</label
            >
            <input
              id="input-verificar-sig"
              v-model="verifySig"
              type="text"
              class="solvency-view__input"
              placeholder="Digest hexadecimal de 64 caracteres"
            />
          </div>

          <button id="btn-verificar-solvencia" type="submit" class="solvency-view__submit">
            Verificar Firma y Vigencia
          </button>

          <div
            v-if="financeStore.data.verificacionSolvencia"
            id="solvencia-verificacion-result"
            class="solvency-view__certificate"
          >
            <strong>
              {{
                financeStore.data.verificacionSolvencia.valido
                  ? 'CERTIFICADO AUTÉNTICO'
                  : 'INVÁLIDO'
              }}
            </strong>
            <span>
              Unidad: {{ financeStore.data.verificacionSolvencia.identificador_unidad }} · Vigente:
              {{ financeStore.data.verificacionSolvencia.vigente ? 'SÍ' : 'NO' }}
            </span>
          </div>
        </form>
      </div>
    </section>
  </AppShellLayout>
</template>

<style scoped>
.solvency-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.solvency-view__title {
  margin: 0;
  font-size: clamp(1.25rem, 3cqi, 1.5rem);
  font-weight: 800;
  color: #0f172a;
  text-wrap: balance;
}

.solvency-view__subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: #475569;
  max-inline-size: 65ch;
}

.solvency-view__alert {
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.solvency-view__alert--warning {
  background-color: #fffbeb;
  border: 1px solid #f59e0b;
  color: #92400e;
}

.solvency-view__alert--success {
  background-color: #ecfdf5;
  border: 1px solid #10b981;
  color: #065f46;
}

.solvency-view__error {
  margin: 0;
  color: #b91c1c;
  font-size: 0.85rem;
  font-weight: 700;
}

.solvency-view__layout {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
  gap: 1rem;
}

.solvency-view__card {
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 0.875rem;
  padding: clamp(1rem, 2.5cqi, 1.25rem);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.solvency-view__card-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
}

.solvency-view__field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.solvency-view__label {
  font-size: 0.8rem;
  font-weight: 700;
  color: #334155;
}

.solvency-view__input {
  padding: 0.55rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #94a3b8;
  font-size: 0.875rem;
}

.solvency-view__submit {
  align-self: flex-start;
  padding: 0.6rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background-color: #0284c7;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.solvency-view__certificate {
  margin-top: 0.5rem;
  padding: 0.875rem;
  border-radius: 0.75rem;
  background-color: #f0fdf4;
  border: 1px solid #86efac;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: #064e3b;
}

.solvency-view__cert-row {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}

.solvency-view__qr-box {
  margin-top: 0.35rem;
  padding: 0.5rem;
  border-radius: 0.5rem;
  background-color: #ffffff;
  border: 1px dashed #10b981;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.solvency-view__qr-label {
  font-size: 0.72rem;
  font-weight: 700;
  color: #047857;
}

.solvency-view__qr-code {
  font-size: 0.72rem;
  word-break: break-all;
  color: #0f172a;
}

.tabular-num {
  font-variant-numeric: tabular-nums;
}

@media (pointer: coarse) {
  .solvency-view__submit {
    min-block-size: 2.75rem;
  }
}
</style>
