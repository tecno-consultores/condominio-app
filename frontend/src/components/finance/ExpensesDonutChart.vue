<script setup lang="ts">
import { computed } from 'vue';
import {
  addDecimalHalfUp,
  compareDecimal,
  divideDecimalHalfUp,
  multiplyDecimalHalfUp,
  roundDecimalHalfUp,
} from '../../utils/decimal';

export interface CategorySlice {
  category: string;
  amountFormatted: string;
  percentage: number;
  dashOffset: number;
  color: string;
}

const props = defineProps<{
  expensesByCategory: Record<string, string>;
  totalExpensesUsd: string;
}>();

const PALETTE = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
];

const slices = computed<CategorySlice[]>(() => {
  const entries = Object.entries(props.expensesByCategory);
  const totalStr = addDecimalHalfUp(
    entries.map(([, val]) => val),
    2,
  );
  if (compareDecimal(totalStr, '0') <= 0) {
    return [];
  }
  let cumulativePercent = 0;
  return entries.map(([category, rawVal], idx) => {
    const pctExact = divideDecimalHalfUp(multiplyDecimalHalfUp(rawVal, '100', 4), totalStr, 4);
    const percentage = Number(roundDecimalHalfUp(pctExact, 0));
    const dashOffset = (125 - cumulativePercent) % 100;
    cumulativePercent += percentage;
    return {
      category,
      amountFormatted: roundDecimalHalfUp(rawVal, 2),
      percentage,
      dashOffset,
      color: PALETTE[idx % PALETTE.length]!,
    };
  });
});
</script>

<template>
  <section
    id="expenses-donut-chart"
    class="expenses-card"
    aria-label="Distribución de gastos por categoría"
  >
    <header class="expenses-card__header">
      <h2 class="expenses-card__title">Distribución de Egresos</h2>
      <strong class="expenses-card__total tabular-nums">Total: {{ totalExpensesUsd }} USD</strong>
    </header>

    <div v-if="slices.length > 0" class="expenses-card__grid">
      <svg
        class="donut-svg"
        viewBox="0 0 42 42"
        role="img"
        aria-label="Gráfico de anillo de gastos"
      >
        <circle
          cx="21"
          cy="21"
          r="15.915"
          fill="transparent"
          stroke="var(--chart-track)"
          stroke-width="5"
        />
        <circle
          v-for="slice in slices"
          :key="slice.category"
          cx="21"
          cy="21"
          r="15.915"
          fill="transparent"
          :stroke="slice.color"
          stroke-width="5"
          :stroke-dasharray="`${slice.percentage} ${100 - slice.percentage}`"
          :stroke-dashoffset="slice.dashOffset"
        />
      </svg>

      <ul class="expenses-legend">
        <li v-for="slice in slices" :key="slice.category" class="expenses-legend__item">
          <span class="expenses-legend__dot" :style="{ backgroundColor: slice.color }" />
          <span class="expenses-legend__name">{{ slice.category }}</span>
          <strong class="expenses-legend__val tabular-nums">
            {{ slice.amountFormatted }} USD ({{ slice.percentage }}%)
          </strong>
        </li>
      </ul>
    </div>
    <p v-else class="expenses-card__empty">No se han registrado egresos en el periodo actual.</p>
  </section>
</template>

<style scoped>
.expenses-card {
  padding: 1.25rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-card);
}

.expenses-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.expenses-card__title {
  margin: 0;
  font-size: 1rem;
  color: var(--text-primary);
}

.expenses-card__total {
  font-size: 0.9rem;
  color: var(--brand-accent);
}

.expenses-card__grid {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1.25rem;
}

.donut-svg {
  width: 120px;
  height: 120px;
  flex-shrink: 0;
}

.expenses-legend {
  list-style: none;
  padding: 0;
  margin: 0;
  flex: 1;
  min-width: 180px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.expenses-legend__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.expenses-legend__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.expenses-legend__name {
  flex: 1;
}

.expenses-legend__val {
  color: var(--text-primary);
}

.expenses-card__empty {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-secondary);
}
</style>
