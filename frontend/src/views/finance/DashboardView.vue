<script setup lang="ts">
import { useRouter } from 'vue-router';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import { useAuthStore } from '../../stores/authStore';

const authStore = useAuthStore();
const router = useRouter();

async function goToReportPayment(): Promise<void> {
  await router.push('/finanzas/reportar-pago');
}
</script>

<template>
  <AppShellLayout>
    <header class="dashboard-header">
      <div>
        <h1 class="dashboard-header__title">Hola, {{ authStore.data?.nombre || 'Vecino' }}</h1>
        <p class="dashboard-header__subtitle">Panel Financiero y Cartelera del Condominio</p>
      </div>
      <div id="daily-rate-badge" class="rate-badge">Tasa BCV: 36.50 VES/USD</div>
    </header>

    <section class="dashboard-summary" aria-label="Resumen rápido">
      <article class="summary-card">
        <h2 class="summary-card__title">Estado de Cuenta</h2>
        <p class="summary-card__value">Solvente / Al día</p>
      </article>
    </section>

    <button id="fab-reportar-pago" type="button" class="fab-button" @click="goToReportPayment">
      Pagar / Reportar
    </button>
  </AppShellLayout>
</template>

<style scoped>
.dashboard-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.dashboard-header__title {
  font-size: 1.35rem;
  margin: 0;
  color: #0f172a;
}

.dashboard-header__subtitle {
  font-size: 0.875rem;
  color: #475569;
  margin: 0.25rem 0 0;
}

.rate-badge {
  padding: 0.5rem 0.875rem;
  border-radius: 9999px;
  background-color: #0f172a;
  color: #38bdf8;
  font-weight: 700;
  font-size: 0.85rem;
}

.summary-card {
  padding: 1.25rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
}

.summary-card__title {
  font-size: 0.95rem;
  color: #475569;
  margin: 0 0 0.5rem;
}

.summary-card__value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.fab-button {
  position: fixed;
  bottom: calc(5rem + env(safe-area-inset-bottom, 0px));
  right: 1rem;
  z-index: 30;
  min-height: 48px;
  padding: 0.75rem 1.25rem;
  border-radius: 9999px;
  border: none;
  background-color: #0284c7;
  color: #ffffff;
  font-weight: 700;
  box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35);
  cursor: pointer;
}
</style>
