<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import SkeletonCard from '../../components/common/SkeletonCard.vue';
import AnnouncementsCarousel from '../../components/finance/AnnouncementsCarousel.vue';
import ClosingBanner from '../../components/finance/ClosingBanner.vue';
import CollectionTrafficLight from '../../components/finance/CollectionTrafficLight.vue';
import ExpensesDonutChart from '../../components/finance/ExpensesDonutChart.vue';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import { runWithViewTransition } from '../../composables/useViewTransition';
import { useAuthStore } from '../../stores/authStore';
import { convertUsdToVes, useFinanceStore } from '../../stores/financeStore';

const authStore = useAuthStore();
const financeStore = useFinanceStore();
const router = useRouter();

const activeTab = ref<'cobranza' | 'gastos'>('cobranza');

const deudaTotalUsd = computed(() => financeStore.data.resumen?.deuda_total_usd ?? '0.00');
const isSolvent = computed(() => Number.parseFloat(deudaTotalUsd.value) <= 0);
const deudaTotalVes = computed(() =>
  convertUsdToVes(deudaTotalUsd.value, financeStore.activeRateValue),
);
const activePeriod = computed(
  () =>
    financeStore.data.ultimoCierre?.periodo ??
    financeStore.data.tasaActiva?.fecha?.slice(0, 7) ??
    new Date().toISOString().slice(0, 7),
);
const ownUnitId = computed(() => authStore.data?.unidad_activa_id ?? null);

onMounted(async () => {
  await financeStore.fetchDashboardData();
});

async function navigateTo(path: string): Promise<void> {
  await runWithViewTransition(() => router.push(path));
}

async function switchTab(tab: 'cobranza' | 'gastos'): Promise<void> {
  if (activeTab.value === tab) {
    return;
  }
  await runWithViewTransition(() => {
    activeTab.value = tab;
  });
}
</script>

<template>
  <AppShellLayout>
    <header class="dashboard-header">
      <div>
        <h1 class="dashboard-header__title">Hola, {{ authStore.data?.nombre || 'Vecino' }}</h1>
        <p class="dashboard-header__subtitle">
          Tu Hogar Hoy — Panel Financiero y Cartelera del Condominio
        </p>
      </div>
      <div id="daily-rate-badge" class="rate-badge tabular-nums">
        Tasa BCV: {{ financeStore.activeRateValue }} VES/USD
      </div>
    </header>

    <ClosingBanner :is-closed="financeStore.isPeriodClosed" :periodo="activePeriod" />

    <section class="dashboard-summary" aria-label="Resumen rápido">
      <article
        id="deuda-card"
        class="summary-card card-elevated"
        :class="isSolvent ? 'hero-solvency--ok' : 'hero-solvency--warn'"
      >
        <div class="hero-solvency__top">
          <div class="hero-solvency__heading">
            <span class="hero-solvency__icon" aria-hidden="true">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M12 3 4 6v6c0 5 3.4 8.4 8 9 4.6-.6 8-4 8-9V6l-8-3Z" />
                <path v-if="isSolvent" d="m9 12 2 2 4-4" />
                <path v-else d="M12 9v4M12 16h.01" />
              </svg>
            </span>
            <div>
              <h2 class="summary-card__title">Estado de Cuenta Consolidado</h2>
              <span
                id="hero-solvency-badge"
                class="hero-solvency__badge"
                :class="isSolvent ? 'hero-solvency__badge--ok' : 'hero-solvency__badge--warn'"
              >
                <span aria-hidden="true">{{ isSolvent ? '✓' : '!' }}</span>
                <span>{{ isSolvent ? 'Al día' : 'Saldo pendiente' }}</span>
              </span>
            </div>
          </div>

          <button
            v-if="isSolvent"
            id="btn-hero-solvencia"
            type="button"
            class="hero-solvency__cta"
            @click="navigateTo('/finanzas/solvencia')"
          >
            Ver Solvencia
          </button>
          <button
            v-else
            id="btn-hero-pagar"
            type="button"
            class="hero-solvency__cta hero-solvency__cta--primary"
            @click="navigateTo('/finanzas/reportar-pago')"
          >
            Reportar Pago
          </button>
        </div>

        <p class="summary-card__value tabular-nums">
          {{ isSolvent ? 'Solvente / Al día' : `${deudaTotalUsd} USD` }}
        </p>
        <p class="summary-card__sub tabular-nums">Equivalente BCV: {{ deudaTotalVes }} VES</p>
      </article>
    </section>

    <section aria-label="Acciones frecuentes" class="quick-actions-section">
      <div id="dashboard-quick-actions" class="quick-actions">
        <button
          id="qa-reportar-pago"
          type="button"
          class="quick-action-btn"
          @click="navigateTo('/finanzas/reportar-pago')"
        >
          Reportar Pago
        </button>
        <button
          id="qa-solvencia"
          type="button"
          class="quick-action-btn"
          @click="navigateTo('/finanzas/solvencia')"
        >
          Certificado de Solvencia
        </button>
        <button
          id="qa-consultas"
          type="button"
          class="quick-action-btn"
          @click="navigateTo('/consultas')"
        >
          Cartas Consulta
        </button>
        <button
          id="qa-incidencias"
          type="button"
          class="quick-action-btn"
          @click="navigateTo('/incidencias')"
        >
          Incidencias
        </button>
      </div>
    </section>

    <SkeletonCard
      v-if="financeStore.isLoading"
      :lines="2"
      height="96px"
      label="Actualizando información financiera..."
    />

    <AnnouncementsCarousel :items="financeStore.data.comunicados" />

    <nav class="dashboard-tabs" aria-label="Secciones financieras">
      <button
        id="tab-cobranza"
        type="button"
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === 'cobranza' }"
        @click="switchTab('cobranza')"
      >
        Semáforo de Cobranza
      </button>
      <button
        id="tab-gastos"
        type="button"
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === 'gastos' }"
        @click="switchTab('gastos')"
      >
        Gastos por Categoría
      </button>
    </nav>

    <CollectionTrafficLight
      v-if="activeTab === 'cobranza'"
      :items="financeStore.data.resumen?.estado_cobranza ?? []"
      :rate-usd-ves="financeStore.activeRateValue"
      :own-unit-id="ownUnitId"
    />
    <ExpensesDonutChart
      v-else
      :expenses-by-category="financeStore.data.resumen?.gastos_por_categoria ?? {}"
      :total-expenses-usd="financeStore.data.resumen?.total_egresos_usd ?? '0.00'"
    />

    <button
      id="fab-reportar-pago"
      type="button"
      class="fab-button"
      @click="navigateTo('/finanzas/reportar-pago')"
    >
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
  color: var(--text-primary, #0f172a);
}

.dashboard-header__subtitle {
  font-size: 0.875rem;
  color: var(--text-secondary, #475569);
  margin: 0.25rem 0 0;
}

.rate-badge {
  padding: 0.5rem 0.875rem;
  border-radius: var(--radius-pill, 9999px);
  background-color: var(--brand-tint, #e0f2fe);
  border: 1px solid var(--border-subtle, #cbd5e1);
  color: var(--brand-accent, #0369a1);
  font-weight: 700;
  font-size: 0.85rem;
}

.dashboard-summary {
  margin-bottom: 1rem;
}

.summary-card {
  padding: clamp(1rem, 2.5cqi, 1.5rem);
  border-radius: var(--radius-lg, 1rem);
  background-color: var(--surface-card, #ffffff);
  border: 1px solid var(--border-subtle, #cbd5e1);
  border-block-start: 4px solid var(--brand-accent, #0369a1);
  box-shadow: var(--surface-hairline), var(--shadow-card);
}

.hero-solvency--ok {
  border-block-start-color: var(--status-ok-border, #16a34a);
  background-color: var(--status-ok-tint, #f0fdf4);
}

.hero-solvency--warn {
  border-block-start-color: var(--status-warn-border, #d97706);
  background-color: var(--status-warn-tint, #fffbeb);
}

.hero-solvency__top {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.hero-solvency__heading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.hero-solvency__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 2.5rem;
  block-size: 2.5rem;
  border-radius: var(--radius-md, 0.75rem);
  background-color: var(--surface-card, #ffffff);
  color: var(--brand-accent, #0369a1);
  border: 1px solid var(--border-subtle, #e2e8f0);
  flex-shrink: 0;
}

.hero-solvency__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-pill, 9999px);
  font-size: 0.75rem;
  font-weight: 700;
}

.hero-solvency__badge--ok {
  background-color: var(--status-ok-bg, #dcfce7);
  color: var(--status-ok-text, #166534);
}

.hero-solvency__badge--warn {
  background-color: var(--status-warn-bg, #fef3c7);
  color: var(--status-warn-text, #92400e);
}

.hero-solvency__cta {
  min-block-size: 2.75rem;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm, 0.5rem);
  border: 1px solid var(--border-control, #94a3b8);
  background-color: var(--surface-card, #ffffff);
  color: var(--text-primary, #0f172a);
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
}

.hero-solvency__cta--primary {
  background-color: var(--brand-600, #0369a1);
  border-color: var(--brand-600, #0369a1);
  color: #ffffff;
}

.summary-card__title {
  font-size: 0.95rem;
  color: var(--text-secondary, #475569);
  margin: 0 0 0.25rem;
}

.summary-card__value {
  font-size: clamp(1.25rem, 1.1rem + 0.75vw, 1.5rem);
  font-weight: 700;
  color: var(--text-primary, #0f172a);
  margin: 0;
}

.summary-card__sub {
  margin: 0.25rem 0 0;
  font-size: 0.85rem;
  color: var(--text-secondary, #475569);
}

.quick-actions-section {
  margin-bottom: 1.25rem;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));
  gap: 0.625rem;
}

.quick-action-btn {
  min-block-size: 2.75rem;
  padding: 0.625rem 0.875rem;
  border-radius: var(--radius-md, 0.75rem);
  border: 1px solid var(--border-subtle, #cbd5e1);
  background-color: var(--surface-card, #ffffff);
  color: var(--text-primary, #0f172a);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}

.quick-action-btn:hover {
  border-color: var(--brand-accent, #0369a1);
  background-color: var(--brand-tint, #f0f9ff);
}

.dashboard-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.tab-btn {
  min-block-size: 2.75rem;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm, 0.5rem);
  border: 1px solid var(--border-control, #cbd5e1);
  background-color: var(--surface-card, #ffffff);
  color: var(--text-secondary, #334155);
  font-weight: 600;
  cursor: pointer;
}

.tab-btn--active {
  background-color: var(--brand-600, #0369a1);
  color: #ffffff;
  border-color: var(--brand-600, #0369a1);
}

.fab-button {
  position: fixed;
  bottom: calc(5.5rem + env(safe-area-inset-bottom, 0px));
  right: clamp(1rem, 3vw, 2rem);
  z-index: 30;
  min-block-size: 3rem;
  padding: 0.75rem 1.25rem;
  border-radius: var(--radius-pill, 9999px);
  border: none;
  background-color: var(--brand-600, #0369a1);
  color: #ffffff;
  font-weight: 700;
  box-shadow: var(--shadow-elevated);
  cursor: pointer;
}

@media (min-width: 768px) {
  .fab-button {
    bottom: clamp(1.5rem, 3vw, 2.5rem);
  }
}
</style>
