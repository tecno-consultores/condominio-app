<script setup lang="ts">
import { onMounted, ref } from 'vue';
import RejectPaymentModal from '../../components/finance/RejectPaymentModal.vue';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import { useFinanceStore } from '../../stores/financeStore';

const financeStore = useFinanceStore();

const rejectModalOpen = ref(false);
const selectedPagoId = ref<number | null>(null);
const actionMessage = ref<string | null>(null);

onMounted(async () => {
  await financeStore.fetchPagosEnRevision();
});

async function handleApprove(pagoId: number): Promise<void> {
  actionMessage.value = null;
  try {
    await financeStore.aprobarPago(pagoId);
    actionMessage.value = `Pago #${pagoId} aprobado e imputado al recibo correspondiente.`;
  } catch {
    // Error almacenado en financeStore.errorMessage
  }
}

function openRejectModal(pagoId: number): void {
  selectedPagoId.value = pagoId;
  rejectModalOpen.value = true;
}

async function handleConfirmReject(payload: { pagoId: number; motivo: string }): Promise<void> {
  actionMessage.value = null;
  try {
    await financeStore.rechazarPago(payload.pagoId, payload.motivo);
    rejectModalOpen.value = false;
    actionMessage.value = `Pago #${payload.pagoId} rechazado con auditoría forense registrada.`;
  } catch {
    // Error almacenado en financeStore.errorMessage
  }
}
</script>

<template>
  <AppShellLayout>
    <header class="page-header">
      <h1 class="page-header__title">Mesa de Conciliación de Pagos (Tesorería)</h1>
      <p class="page-header__subtitle">
        Aprueba abonos conciliados en banco o recházalos dejando trazabilidad forense obligatoria.
      </p>
    </header>

    <div v-if="financeStore.errorMessage" class="banner banner--error" role="alert">
      {{ financeStore.errorMessage }}
    </div>
    <div v-if="actionMessage" class="banner banner--success" role="status">
      {{ actionMessage }}
    </div>

    <section aria-label="Pagos pendientes de revisión">
      <p v-if="financeStore.data.pagosEnRevision.length === 0" class="empty-state">
        No existen pagos pendientes de revisión en este momento.
      </p>

      <div v-else class="payment-grid">
        <article
          v-for="pago in financeStore.data.pagosEnRevision"
          :key="pago.id"
          class="payment-card"
        >
          <div class="payment-card__header">
            <strong>Pago #{{ pago.id }} — Recibo #{{ pago.recibo_id }}</strong>
            <span class="payment-card__method">{{ pago.metodo_pago }}</span>
          </div>

          <p class="payment-card__amount">
            {{ pago.monto }} {{ pago.moneda }} (<strong>{{ pago.monto_usd }} USD</strong> a tasa
            {{ pago.tasa_cambio }})
          </p>
          <p class="payment-card__ref">
            Referencia: <strong>{{ pago.numero_referencia || 'Efectivo en taquilla' }}</strong>
          </p>

          <div class="payment-card__actions">
            <button
              type="button"
              class="btn-approve-payment"
              :disabled="financeStore.isLoading"
              @click="handleApprove(pago.id)"
            >
              Aprobar Pago
            </button>
            <button
              type="button"
              class="btn-reject-payment"
              :disabled="financeStore.isLoading"
              @click="openRejectModal(pago.id)"
            >
              Rechazar
            </button>
          </div>
        </article>
      </div>
    </section>

    <RejectPaymentModal
      :open="rejectModalOpen"
      :pago-id="selectedPagoId"
      @close="rejectModalOpen = false"
      @confirm="handleConfirmReject"
    />
  </AppShellLayout>
</template>

<style scoped>
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

.empty-state {
  padding: 1.5rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
}

.payment-grid {
  display: grid;
  gap: 1rem;
}

.payment-card {
  padding: 1.25rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
}

.payment-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.payment-card__method {
  padding: 0.2rem 0.55rem;
  border-radius: 9999px;
  background-color: #e0f2fe;
  color: #0369a1;
  font-size: 0.75rem;
  font-weight: 700;
}

.payment-card__amount,
.payment-card__ref {
  margin: 0.25rem 0;
  font-size: 0.9rem;
  color: #1e293b;
}

.payment-card__actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

.btn-approve-payment {
  min-height: 44px;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background-color: #16a34a;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.btn-reject-payment {
  min-height: 44px;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #dc2626;
  background-color: #ffffff;
  color: #dc2626;
  font-weight: 700;
  cursor: pointer;
}
</style>
