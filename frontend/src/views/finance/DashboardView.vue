<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import AnnouncementsCarousel from '../../components/finance/AnnouncementsCarousel.vue';
import ClosingBanner from '../../components/finance/ClosingBanner.vue';
import CollectionTrafficLight from '../../components/finance/CollectionTrafficLight.vue';
import ExpensesDonutChart from '../../components/finance/ExpensesDonutChart.vue';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import { useAuthStore } from '../../stores/authStore';
import { convertUsdToVes, useFinanceStore } from '../../stores/financeStore';

const authStore = useAuthStore();
const financeStore = useFinanceStore();
const router = useRouter();

const activeTab = ref<'cobranza' | 'gastos'>('cobranza');

const deudaTotalUsd = computed(() => financeStore.data.resumen?.deuda_total_usd ?? '0.00');
const deudaTotalVes = computed(() =>
  convertUsdToVes(deudaTotalUsd.value, financeStore.activeRateValue),
);

onMounted(async () => {
  await financeStore.fetchDashboardData();
});

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
      <div id="daily-rate-badge" class="rate-badge">
        Tasa BCV: {{ financeStore.activeRateValue }} VES/USD
      </div>
    </header>

    <ClosingBanner :is-closed="financeStore.isPeriodClosed" periodo="2026-10" />

    <section class="dashboard-summary" aria-label="Resumen rápido">
      <article id="deuda-card" class="summary-card">
        <h2 class="summary-card__title">Estado de Cuenta Consolidado</h2>
        <p class="summary-card__value">
          {{ Number.parseFloat(deudaTotalUsd) <= 0 ? 'Solvente / Al día' : `${deudaTotalUsd} USD` }}
        </p>
        <p class="summary-card__sub">Equivalente BCV: {{ deudaTotalVes }} VES</p>
      </article>
    </section>

    <AnnouncementsCarousel :items="financeStore.data.comunicados" />

    <nav class="dashboard-tabs" aria-label="Secciones financieras">
      <button
        id="tab-cobranza"
        type="button"
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === 'cobranza' }"
        @click="activeTab = 'cobranza'"
      >
        Semáforo de Cobranza
      </button>
      <button
        id="tab-gastos"
        type="button"
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === 'gastos' }"
        @click="activeTab = 'gastos'"
      >
        Gastos por Categoría
      </button>
    </nav>

    <CollectionTrafficLight
      v-if="activeTab === 'cobranza'"
      :items="financeStore.data.resumen?.estado_cobranza ?? []"
      :rate-usd-ves="financeStore.activeRateValue"
    />
    <ExpensesDonutChart
      v-else
      :expenses-by-category="financeStore.data.resumen?.gastos_por_categoria ?? {}"
      :total-expenses-usd="financeStore.data.resumen?.total_egresos_usd ?? '0.00'"
    />

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
  margin-bottom: 1.25rem;
}

.dashboard-header__title {
  font-size: clamp(1.2rem, 1rem + 1vw, 1.5rem);
  text-wrap: balance;
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
  font-variant-numeric: tabular-nums;
}

.dashboard-summary {
  margin-bottom: 1.25rem;
}

.summary-card {
  padding: clamp(1rem, 2.5cqi, 1.5rem);
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  box-shadow:
    0 1px 3px 0 rgba(15, 23, 42, 0.06),
    0 1px 2px -1px rgba(15, 23, 42, 0.06);
}

.summary-card__title {
  font-size: 0.95rem;
  color: #475569;
  margin: 0 0 0.5rem;
}

.summary-card__value {
  font-size: clamp(1.25rem, 1.1rem + 0.75vw, 1.5rem);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: #0f172a;
  margin: 0;
}

.summary-card__sub {
  margin: 0.25rem 0 0;
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
  color: #475569;
}

.dashboard-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.tab-btn {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  background-color: #ffffff;
  color: #334155;
  font-weight: 600;
  cursor: pointer;
}

@media (pointer: coarse) {
  .tab-btn {
    min-block-size: 2.75rem;
  }
}

.tab-btn--active {
  background-color: #0f172a;
  color: #38bdf8;
  border-color: #0f172a;
}

.fab-button {
  position: fixed;
  bottom: calc(4.75rem + env(safe-area-inset-bottom, 0px));
  right: clamp(1rem, 3vw, 2rem);
  z-index: 30;
  padding: 0.75rem 1.25rem;
  border-radius: 9999px;
  border: none;
  background-color: #0284c7;
  color: #ffffff;
  font-weight: 700;
  box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35);
  cursor: pointer;
}

@media (pointer: coarse) {
  .fab-button {
    min-block-size: 3rem;
  }
}

@media (min-width: 768px) {
  .fab-button {
    bottom: clamp(1.5rem, 3vw, 2.5rem);
  }
}
</style>
