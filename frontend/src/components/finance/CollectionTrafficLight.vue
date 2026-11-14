<script setup lang="ts">
import { computed } from 'vue';
import { convertUsdToVes, type EstadoCobranzaItemDTO } from '../../stores/financeStore';

const props = withDefaults(
  defineProps<{
    items: EstadoCobranzaItemDTO[];
    rateUsdVes: string;
    ownUnitId?: number | null;
  }>(),
  {
    ownUnitId: null,
  },
);

const sortedItems = computed<EstadoCobranzaItemDTO[]>(() => {
  return [...props.items].sort((a, b) => {
    if (props.ownUnitId !== null) {
      if (a.unidad_id === props.ownUnitId && b.unidad_id !== props.ownUnitId) return -1;
      if (b.unidad_id === props.ownUnitId && a.unidad_id !== props.ownUnitId) return 1;
    }
    return a.unidad_id - b.unidad_id;
  });
});

function formatVes(saldoUsd: string): string {
  return convertUsdToVes(saldoUsd, props.rateUsdVes);
}

const STATUS_GLYPHS: Record<string, string> = {
  SOLVENTE: '✓',
  PAGADO: '✓',
  ABONO_PARCIAL: '◐',
  PARCIAL: '◐',
  PENDIENTE: '!',
  MOROSO: '✕',
  VENCIDO: '✕',
  RECHAZADO: '✕',
};

function glyphFor(estado: string): string {
  return STATUS_GLYPHS[estado.toUpperCase()] ?? '•';
}
</script>

<template>
  <div
    id="collection-traffic-light"
    tabindex="0"
    role="region"
    aria-labelledby="collection-table-caption"
    class="table-wrapper"
  >
    <table class="collection-table">
      <caption id="collection-table-caption" class="collection-table__caption">
        Semáforo de cobranza por unidad y saldo en USD / VES
      </caption>
      <thead>
        <tr>
          <th scope="col">Unidad</th>
          <th scope="col">Periodo</th>
          <th scope="col">Estado</th>
          <th scope="col">Saldo (USD / VES)</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="sortedItems.length === 0">
          <th scope="row" colspan="4" class="collection-table__empty">
            No existen recibos emitidos para el periodo seleccionado.
          </th>
        </tr>
        <tr
          v-for="item in sortedItems"
          :key="`${item.unidad_id}-${item.periodo}`"
          class="collection-row"
          :class="{ 'collection-row--own': ownUnitId === item.unidad_id }"
        >
          <th scope="row">
            Unidad #{{ item.unidad_id }}
            <span v-if="ownUnitId === item.unidad_id" class="own-badge">(Tu unidad)</span>
          </th>
          <td>{{ item.periodo }}</td>
          <td>
            <span class="status-pill" :class="`status-pill--${item.estado.toLowerCase()}`">
              <span class="status-pill__glyph" aria-hidden="true">{{ glyphFor(item.estado) }}</span>
              <span>{{ item.estado }}</span>
            </span>
          </td>
          <td>
            <strong class="tabular-nums">{{ item.saldo_usd }} USD</strong>
            <span class="ves-subtext tabular-nums">({{ formatVes(item.saldo_usd) }} VES)</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrapper {
  overflow: auto;
  max-inline-size: 100%;
  max-block-size: min(32rem, 75dvh);
  container-type: inline-size;
  background-color: var(--surface-card, #ffffff);
  border: 1px solid var(--border-subtle, #cbd5e1);
  border-radius: var(--radius-md, 0.75rem);
  box-shadow: var(--shadow-card);
}

.collection-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-variant-numeric: tabular-nums;
  --label-2: 'Periodo';
  --label-3: 'Estado';
  --label-4: 'Saldo (USD / VES)';
}

.collection-table__caption {
  text-align: left;
  padding: 0.875rem 1rem;
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--text-primary, #0f172a);
  border-bottom: 1px solid var(--border-subtle, #e2e8f0);
}

thead {
  position: sticky;
  inset-block-start: 0;
  z-index: 2;
  background-color: var(--surface-subtle, #f8fafc);
}

thead th:first-child {
  position: sticky;
  inset-inline-start: 0;
  z-index: 3;
  background-color: var(--surface-subtle, #f8fafc);
}

th,
td {
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.85rem;
  color: var(--text-primary, #0f172a);
  border-bottom: 1px solid var(--border-subtle, #f1f5f9);
}

tbody th {
  position: sticky;
  inset-inline-start: 0;
  z-index: 1;
  background-color: var(--surface-card, #ffffff);
  font-weight: 700;
  color: var(--text-primary, #0f172a);
}

tbody tr.collection-row--own th,
tbody tr.collection-row--own td {
  background-color: var(--brand-tint, #f0f9ff);
}

@container (min-width: 600px) {
  th:nth-child(4),
  td:nth-child(4) {
    text-align: right;
  }
}

.own-badge {
  margin-left: 0.375rem;
  font-size: 0.75rem;
  color: var(--brand-accent, #0369a1);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-pill, 9999px);
  font-size: 0.75rem;
  font-weight: 700;
}

.status-pill--solvente,
.status-pill--pagado {
  background-color: var(--status-ok-bg, #dcfce7);
  color: var(--status-ok-text, #166534);
}

.status-pill--abono_parcial,
.status-pill--parcial {
  background-color: var(--status-warn-bg, #fef3c7);
  color: var(--status-warn-text, #92400e);
}

.status-pill--pendiente,
.status-pill--moroso,
.status-pill--vencido,
.status-pill--rechazado {
  background-color: var(--status-danger-bg, #fee2e2);
  color: var(--status-danger-text, #991b1b);
}

.ves-subtext {
  display: inline-block;
  margin-left: 0.375rem;
  color: var(--text-secondary, #475569);
  font-size: 0.8rem;
}

@container (max-width: 599px) {
  .collection-table,
  thead,
  tbody,
  tr,
  th,
  td {
    display: block;
  }

  thead {
    /* MANDATORY: Hide column header from layout and screen readers. */
    display: none;
  }

  tr {
    margin-block-end: 0.75rem;
    border: 1px solid var(--border-subtle, #cbd5e1);
    border-radius: var(--radius-sm, 0.5rem);
  }

  tbody th {
    position: sticky;
    inset-block-start: 0;
    z-index: 2;
    background-color: var(--surface-subtle, #f1f5f9);
  }

  td:nth-child(2)::before {
    content: var(--label-2) ': ';
    font-weight: 600;
  }

  td:nth-child(3)::before {
    content: var(--label-3) ': ';
    font-weight: 600;
  }

  td:nth-child(4)::before {
    content: var(--label-4) ': ';
    font-weight: 600;
  }
}
</style>
