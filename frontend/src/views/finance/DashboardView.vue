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
import { useDualRefresh } from '../../composables/useDualRefresh';
import { runWithViewTransition } from '../../composables/useViewTransition';
import { useAuthStore } from '../../stores/authStore';
import { convertUsdToVes, useFinanceStore } from '../../stores/financeStore';
import { useOperationsStore } from '../../stores/operationsStore';
import { compareDecimal } from '../../utils/decimal';

type DashboardTab = 'cobranza' | 'gastos';

const authStore = useAuthStore();
const financeStore = useFinanceStore();
const operationsStore = useOperationsStore();
const router = useRouter();

const activeTab = ref<DashboardTab>('cobranza');
const tabCobranzaRef = ref<HTMLButtonElement | null>(null);
const tabGastosRef = ref<HTMLButtonElement | null>(null);

const hasResumen = computed(() => financeStore.data.resumen !== null);
const deudaTotalUsd = computed(() => financeStore.data.resumen?.deuda_total_usd ?? '0.00');
const isSolvent = computed(() => hasResumen.value && compareDecimal(deudaTotalUsd.value, '0') <= 0);
const hasOfficialRate = computed(
  () =>
    financeStore.activeRateValue !== null && compareDecimal(financeStore.activeRateValue, '0') > 0,
);
const deudaTotalVes = computed<string | null>(() => {
  if (!hasResumen.value || !hasOfficialRate.value || !financeStore.activeRateValue) {
    return null;
  }
  return convertUsdToVes(deudaTotalUsd.value, financeStore.activeRateValue);
});
const activePeriod = computed(
  () =>
    financeStore.data.ultimoCierre?.periodo ??
    financeStore.data.tasaActiva?.fecha?.slice(0, 7) ??
    new Date().toISOString().slice(0, 7),
);
const ownUnitId = computed(() => authStore.activeUnitId);
const unitLabels = computed<Record<number, string>>(() => {
  const labels: Record<number, string> = {};
  for (const unidad of operationsStore.data.unidades) {
    labels[unidad.id] = unidad.identificador;
  }
  return labels;
});

const heroCardClass = computed(() => {
  if (!hasResumen.value) {
    return 'hero-solvency--neutral';
  }
  return isSolvent.value ? 'hero-solvency--ok' : 'hero-solvency--warn';
});

const heroBadgeClass = computed(() => {
  if (!hasResumen.value) {
    return 'hero-solvency__badge--neutral';
  }
  return isSolvent.value ? 'hero-solvency__badge--ok' : 'hero-solvency__badge--warn';
});

const heroBadgeSymbol = computed(() => {
  if (!hasResumen.value) {
    return '—';
  }
  return isSolvent.value ? '✓' : '!';
});

const heroBadgeText = computed(() => {
  if (!hasResumen.value) {
    return 'Sin datos';
  }
  return isSolvent.value ? 'Al día' : 'Saldo pendiente';
});

async function refreshDashboardData(): Promise<void> {
  await Promise.allSettled([financeStore.fetchDashboardData(), operationsStore.fetchUnidades()]);
}

const { isRefreshing, triggerRefresh } = useDualRefresh(refreshDashboardData);

onMounted(async () => {
  await refreshDashboardData();
});

async function navigateTo(path: string): Promise<void> {
  await runWithViewTransition(() => router.push(path));
}

async function switchTab(tab: DashboardTab): Promise<void> {
  if (activeTab.value === tab) {
    return;
  }
  await runWithViewTransition(() => {
    activeTab.value = tab;
  });
}

function getTargetTabForKey(key: string, current: DashboardTab): DashboardTab | null {
  if (key === 'Home') {
    return 'cobranza';
  }
  if (key === 'End') {
    return 'gastos';
  }
  if (key === 'ArrowRight' || key === 'ArrowLeft') {
    return current === 'cobranza' ? 'gastos' : 'cobranza';
  }
  return null;
}

async function onTabKeydown(event: KeyboardEvent, current: DashboardTab): Promise<void> {
  const target = getTargetTabForKey(event.key, current);
  if (!target) {
    return;
  }
  event.preventDefault();
  await switchTab(target);
  const targetRef = target === 'cobranza' ? tabCobranzaRef.value : tabGastosRef.value;
  targetRef?.focus();
}
</script>

<template>
  <div class="dashboard-view">
    <header class="dashboard-header">
      <div>
        <h1 class="dashboard-header__title">Hola, {{ authStore.data?.nombre || 'Vecino' }}</h1>
        <p class="dashboard-header__subtitle">
          Tu Hogar Hoy — Panel Financiero y Cartelera del Condominio
        </p>
      </div>
      <div class="dashboard-header__actions">
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
        <div id="daily-rate-badge" class="rate-badge tabular-nums">
          <template v-if="financeStore.activeRateValue !== null">
            Tasa BCV: {{ financeStore.activeRateValue }} VES/USD
          </template>
          <template v-else>Tasa BCV pendiente hoy</template>
        </div>
      </div>
    </header>

    <ClosingBanner :is-closed="financeStore.isPeriodClosed" :periodo="activePeriod" />

    <p
      v-if="financeStore.errorMessage"
      id="dashboard-error-banner"
      role="alert"
      class="dashboard-alert"
    >
      {{ financeStore.errorMessage }}
    </p>

    <section class="dashboard-summary" aria-label="Resumen rápido">
      <article id="deuda-card" class="summary-card card-elevated" :class="heroCardClass">
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
                <path v-if="!hasResumen" d="M12 8v4l2 2" />
                <path v-else-if="isSolvent" d="m9 12 2 2 4-4" />
                <path v-else d="M12 9v4M12 16h.01" />
              </svg>
            </span>
            <div>
              <h2 class="summary-card__title">Estado de Cuenta Consolidado</h2>
              <span id="hero-solvency-badge" class="hero-solvency__badge" :class="heroBadgeClass">
                <span aria-hidden="true">{{ heroBadgeSymbol }}</span>
                <span>{{ heroBadgeText }}</span>
              </span>
            </div>
          </div>

          <button
            v-if="hasResumen && isSolvent"
            id="btn-hero-solvencia"
            type="button"
            class="hero-solvency__cta"
            @click="navigateTo('/finanzas/solvencia')"
          >
            Ver Solvencia
          </button>
          <button
            v-else-if="hasResumen"
            id="btn-hero-pagar"
            type="button"
            class="hero-solvency__cta hero-solvency__cta--primary"
            @click="navigateTo('/finanzas/reportar-pago')"
          >
            Reportar Pago
          </button>
          <button
            v-else
            id="btn-hero-refresh"
            type="button"
            class="hero-solvency__cta"
            :disabled="isRefreshing"
            @click="triggerRefresh"
          >
            Reintentar consulta
          </button>
        </div>

        <p class="summary-card__value tabular-nums">
          <template v-if="!hasResumen">Resumen financiero no disponible</template>
          <template v-else-if="isSolvent">Solvente / Al día</template>
          <template v-else>{{ deudaTotalUsd }} USD</template>
        </p>
        <p class="summary-card__sub tabular-nums">
          <template v-if="!hasResumen">
            Sincroniza la conexión para verificar tu estado de cuenta.
          </template>
          <template v-else-if="deudaTotalVes !== null">
            Equivalente BCV: {{ deudaTotalVes }} VES
          </template>
          <template v-else>Equivalente BCV: Pendiente tasa oficial</template>
        </p>
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

    <div class="dashboard-tabs" role="tablist" aria-label="Secciones financieras">
      <button
        id="tab-cobranza"
        ref="tabCobranzaRef"
        type="button"
        role="tab"
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === 'cobranza' }"
        :aria-selected="activeTab === 'cobranza'"
        aria-controls="panel-cobranza"
        :tabindex="activeTab === 'cobranza' ? 0 : -1"
        @click="switchTab('cobranza')"
        @keydown="onTabKeydown($event, 'cobranza')"
      >
        Semáforo de Cobranza
      </button>
      <button
        id="tab-gastos"
        ref="tabGastosRef"
        type="button"
        role="tab"
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === 'gastos' }"
        :aria-selected="activeTab === 'gastos'"
        aria-controls="panel-gastos"
        :tabindex="activeTab === 'gastos' ? 0 : -1"
        @click="switchTab('gastos')"
        @keydown="onTabKeydown($event, 'gastos')"
      >
        Gastos por Categoría
      </button>
    </div>

    <div
      id="panel-cobranza"
      role="tabpanel"
      aria-labelledby="tab-cobranza"
      :hidden="activeTab !== 'cobranza'"
    >
      <CollectionTrafficLight
        v-if="activeTab === 'cobranza'"
        :items="financeStore.data.resumen?.estado_cobranza ?? []"
        :rate-usd-ves="financeStore.activeRateValue"
        :own-unit-id="ownUnitId"
        :unit-labels="unitLabels"
      />
    </div>
    <div
      id="panel-gastos"
      role="tabpanel"
      aria-labelledby="tab-gastos"
      :hidden="activeTab !== 'gastos'"
    >
      <ExpensesDonutChart
        v-if="activeTab === 'gastos'"
        :expenses-by-category="financeStore.data.resumen?.gastos_por_categoria ?? {}"
        :total-expenses-usd="financeStore.data.resumen?.total_egresos_usd ?? '0.00'"
      />
    </div>

    <button
      id="fab-reportar-pago"
      type="button"
      class="fab-button"
      @click="navigateTo('/finanzas/reportar-pago')"
    >
      Pagar / Reportar
    </button>
  </div>
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

.dashboard-header__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.625rem;
}

.dashboard-header__title {
  font-size: clamp(1.2rem, 1rem + 1vw, 1.5rem);
  text-wrap: balance;
  margin: 0;
  color: var(--text-primary);
}

.dashboard-header__subtitle {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0.25rem 0 0;
}

.rate-badge {
  min-block-size: 2.75rem;
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 0.875rem;
  border-radius: var(--radius-pill);
  background-color: var(--brand-tint);
  border: 1px solid var(--border-subtle);
  color: var(--brand-accent);
  font-weight: 700;
  font-size: 0.85rem;
}

.dashboard-alert {
  margin: 0 0 1rem;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--status-warn-border);
  background-color: var(--status-warn-tint);
  color: var(--status-warn-text);
  font-size: 0.875rem;
  font-weight: 600;
}

.dashboard-summary {
  margin-bottom: 1rem;
}

.summary-card {
  padding: clamp(1rem, 2.5cqi, 1.5rem);
  border-radius: var(--radius-lg);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-block-start: 4px solid var(--brand-accent);
  box-shadow: var(--surface-hairline), var(--shadow-card);
}

.hero-solvency--ok {
  border-block-start-color: var(--status-ok-border);
  background-color: var(--status-ok-tint);
}

.hero-solvency--warn {
  border-block-start-color: var(--status-warn-border);
  background-color: var(--status-warn-tint);
}

.hero-solvency--neutral {
  border-block-start-color: var(--border-control);
  background-color: var(--surface-card);
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
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  color: var(--brand-accent);
  border: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.hero-solvency__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-pill);
  font-size: 0.75rem;
  font-weight: 700;
}

.hero-solvency__badge--ok {
  background-color: var(--status-ok-bg);
  color: var(--status-ok-text);
}

.hero-solvency__badge--warn {
  background-color: var(--status-warn-bg);
  color: var(--status-warn-text);
}

.hero-solvency__badge--neutral {
  background-color: var(--surface-subtle);
  color: var(--text-secondary);
}

.hero-solvency__cta {
  min-block-size: 2.75rem;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-card);
  color: var(--text-primary);
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
}

.hero-solvency__cta--primary {
  background-color: var(--brand-600);
  border-color: var(--brand-600);
  color: var(--text-on-accent);
}

.summary-card__title {
  font-size: 0.95rem;
  color: var(--text-secondary);
  margin: 0 0 0.25rem;
}

.summary-card__value {
  font-size: clamp(1.25rem, 1.1rem + 0.75vw, 1.5rem);
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.summary-card__sub {
  margin: 0.25rem 0 0;
  font-size: 0.85rem;
  color: var(--text-secondary);
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
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background-color: var(--surface-card);
  color: var(--text-primary);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}

.quick-action-btn:hover {
  border-color: var(--brand-accent);
  background-color: var(--brand-tint);
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
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-card);
  color: var(--text-secondary);
  font-weight: 600;
  cursor: pointer;
}

.tab-btn[aria-selected='true'] {
  background-color: var(--brand-600);
  color: var(--text-on-accent);
  border-color: var(--brand-600);
}

.fab-button {
  position: fixed;
  bottom: calc(5.5rem + env(safe-area-inset-bottom, 0px));
  right: clamp(1rem, 3vw, 2rem);
  z-index: 30;
  min-block-size: 3rem;
  padding: 0.75rem 1.25rem;
  border-radius: var(--radius-pill);
  border: none;
  background-color: var(--brand-600);
  color: var(--text-on-accent);
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
