<script setup lang="ts">
import { computed } from 'vue';

export interface CategorySlice {
  category: string;
  amountUsd: number;
  percentage: number;
  color: string;
}

const props = defineProps<{
  expensesByCategory: Record<string, string>;
  totalExpensesUsd: string;
}>();

const PALETTE = ['#0284c7', '#0d9488', '#6366f1', '#f59e0b', '#ec4899'];

const slices = computed<CategorySlice[]>(() => {
  const entries = Object.entries(props.expensesByCategory);
  const total = entries.reduce((sum, [, val]) => sum + Number.parseFloat(val), 0);
  if (total <= 0) {
    return [];
  }
  return entries.map(([category, rawVal], idx) => {
    const amountUsd = Number.parseFloat(rawVal);
    const percentage = Math.round((amountUsd / total) * 100);
    return {
      category,
      amountUsd,
      percentage,
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
      <strong class="expenses-card__total">Total: {{ totalExpensesUsd }} USD</strong>
    </header>

    <div v-if="slices.length > 0" class="expenses-card__grid">
      <svg
        class="donut-svg"
        viewBox="0 0 42 42"
        role="img"
        aria-label="Gráfico de anillo de gastos"
      >
        <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="#e2e8f0" stroke-width="5" />
        <circle
          v-for="(slice, idx) in slices"
          :key="slice.category"
          cx="21"
          cy="21"
          r="15.915"
          fill="transparent"
          :stroke="slice.color"
          stroke-width="5"
          :stroke-dasharray="`${slice.percentage} ${100 - slice.percentage}`"
          :stroke-dashoffset="idx * 25"
        />
      </svg>

      <ul class="expenses-legend">
        <li v-for="slice in slices" :key="slice.category" class="expenses-legend__item">
          <span class="expenses-legend__dot" :style="{ backgroundColor: slice.color }" />
          <span class="expenses-legend__name">{{ slice.category }}</span>
          <strong class="expenses-legend__val">
            {{ slice.amountUsd.toFixed(2) }} USD ({{ slice.percentage }}%)
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
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
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
  color: #0f172a;
}

.expenses-card__total {
  font-size: 0.9rem;
  color: #0284c7;
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
  min-width: 200px;
}

.expenses-legend__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0;
  font-size: 0.85rem;
  border-bottom: 1px solid #f1f5f9;
}

.expenses-legend__dot {
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  flex-shrink: 0;
}

.expenses-legend__name {
  flex: 1;
  color: #334155;
}

.expenses-legend__val {
  color: #0f172a;
}

.expenses-card__empty {
  margin: 0;
  font-size: 0.85rem;
  color: #64748b;
}
</style>
