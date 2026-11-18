<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import EmptyStateCard from '../../components/common/EmptyStateCard.vue';
import SkeletonCard from '../../components/common/SkeletonCard.vue';
import RejectPaymentModal from '../../components/finance/RejectPaymentModal.vue';
import { useDualRefresh } from '../../composables/useDualRefresh';
import { useFinanceStore } from '../../stores/financeStore';
import { isSafeMediaUrl } from '../../utils/security';

const financeStore = useFinanceStore();

const rejectModalOpen = ref(false);
const selectedPagoId = ref<number | null>(null);
const actionMessage = ref<string | null>(null);

const { isRefreshing, triggerRefresh } = useDualRefresh(() => financeStore.fetchPagosEnRevision());

onMounted(async () => {
  await financeStore.fetchPagosEnRevision();
});

async function handleApprove(pagoId: number): Promise<void> {
  actionMessage.value = null;
  try {
    await financeStore.aprobarPago(pagoId);
    actionMessage.value = 'Pago aprobado e imputado al recibo correspondiente.';
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
    actionMessage.value = 'Pago rechazado con auditoría forense registrada.';
  } catch {
    // Error almacenado en financeStore.errorMessage
  }
}

function isProcessingProof(url: string | null | undefined): boolean {
  return Boolean(url && url.trim().startsWith('s3://'));
}
</script>

<template>
  <section aria-labelledby="treasury-payments-title">
    <header class="page-header">
      <div>
        <h1 id="treasury-payments-title" class="page-header__title">
          Mesa de Conciliación de Pagos (Tesorería)
        </h1>
        <p class="page-header__subtitle">
          Aprueba abonos conciliados en banco o recházalos dejando trazabilidad forense obligatoria.
        </p>
      </div>
      <button
        id="btn-dual-refresh"
        type="button"
        class="dual-refresh-btn"
        :disabled="isRefreshing || financeStore.isLoading"
        @click="triggerRefresh"
      >
        <span aria-hidden="true">🔄</span>
        <span>{{ isRefreshing ? 'Actualizando...' : 'Refrescar' }}</span>
      </button>
    </header>

    <div v-if="financeStore.errorMessage" class="banner banner--error" role="alert">
      {{ financeStore.errorMessage }}
    </div>
    <div v-if="actionMessage" class="banner banner--success" role="status">
      {{ actionMessage }}
    </div>

    <section aria-label="Pagos pendientes de revisión">
      <SkeletonCard
        v-if="financeStore.isLoading && financeStore.data.pagosEnRevision.length === 0"
        :lines="3"
        height="130px"
        label="Cargando pagos por aprobar..."
      />
      <EmptyStateCard
        v-else-if="financeStore.data.pagosEnRevision.length === 0"
        class="empty-state"
        title="Conciliación bancaria al día"
        description="No existen pagos pendientes de revisión en este momento."
        icon="check"
      />

      <div v-else class="payment-grid">
        <article
          v-for="pago in financeStore.data.pagosEnRevision"
          :key="pago.id"
          class="payment-card"
        >
          <div class="payment-card__header">
            <strong>Abono reportado — {{ pago.metodo_pago }}</strong>
            <span class="payment-card__method">{{ pago.estado }}</span>
          </div>

          <p class="payment-card__amount tabular-nums">
            {{ pago.monto }} {{ pago.moneda }} (<strong>{{ pago.monto_usd }} USD</strong> a tasa
            {{ pago.tasa_cambio }})
          </p>
          <p class="payment-card__ref">
            Referencia: <strong>{{ pago.numero_referencia || 'Efectivo en taquilla' }}</strong>
          </p>

          <p v-if="isSafeMediaUrl(pago.url_comprobante)" class="payment-card__proof">
            <a
              :href="pago.url_comprobante!.trim()"
              target="_blank"
              rel="noopener noreferrer"
              class="payment-card__proof-link"
            >
              Ver comprobante digital
            </a>
          </p>
          <p v-else-if="isProcessingProof(pago.url_comprobante)" class="payment-card__proof">
            <span class="payment-card__proof-pending">
              Comprobante en procesamiento multimedia
            </span>
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
  </section>
</template>

<style scoped>
.page-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
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

.empty-state {
  padding: 1.5rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

.payment-grid {
  display: grid;
  gap: 1rem;
}

.payment-card {
  padding: 1.25rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-card);
}

.payment-card__header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.payment-card__method {
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-pill);
  background-color: var(--brand-tint);
  color: var(--brand-accent);
  font-size: 0.75rem;
  font-weight: 700;
}

.payment-card__amount,
.payment-card__ref,
.payment-card__proof {
  margin: 0.25rem 0;
  font-size: 0.9rem;
  color: var(--text-primary);
}

.payment-card__proof-link {
  display: inline-flex;
  align-items: center;
  min-block-size: 2.75rem;
  color: var(--brand-accent);
  font-weight: 700;
  text-decoration: underline;
}

.payment-card__proof-pending {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-pill);
  background-color: var(--status-info-bg);
  color: var(--status-info-text);
  font-size: 0.8rem;
  font-weight: 600;
}

.payment-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1rem;
}

.btn-approve-payment {
  min-block-size: 2.75rem;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--status-ok-border);
  background-color: var(--status-ok-bg);
  color: var(--status-ok-text);
  font-weight: 700;
  cursor: pointer;
}

.btn-reject-payment {
  min-block-size: 2.75rem;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--status-danger-border);
  background-color: var(--status-danger-bg);
  color: var(--status-danger-text);
  font-weight: 700;
  cursor: pointer;
}
</style>
