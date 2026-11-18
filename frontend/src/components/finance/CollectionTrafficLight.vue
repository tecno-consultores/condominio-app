<script setup lang="ts">
import { computed } from 'vue';
import { convertUsdToVes, type EstadoCobranzaItemDTO } from '../../stores/financeStore';
import { compareDecimal } from '../../utils/decimal';

const props = withDefaults(
  defineProps<{
    items: EstadoCobranzaItemDTO[];
    rateUsdVes: string | null;
    ownUnitId?: number | null;
    unitLabels?: Record<number, string>;
  }>(),
  {
    ownUnitId: null,
    unitLabels: () => ({}),
  },
);

const hasOfficialRate = computed(
  () => props.rateUsdVes !== null && compareDecimal(props.rateUsdVes, '0') > 0,
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
  if (!hasOfficialRate.value || !props.rateUsdVes) {
    return 'Pendiente tasa BCV';
  }
  return `${convertUsdToVes(saldoUsd, props.rateUsdVes)} VES`;
}

function labelForUnit(unidadId: number): string {
  const custom = props.unitLabels[unidadId];
  if (custom) {
    return custom;
  }
  return props.ownUnitId === unidadId ? 'Tu inmueble asignado' : 'Inmueble registrado';
}

const STATUS_GLYPHS: Record<string, string> = {
  SOLVENTE: '✓',
  PAGADO: '✓',
  PAGADO_PARCIAL: '◐',
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
            {{ labelForUnit(item.unidad_id) }}
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
            <span class="ves-subtext tabular-nums">({{ formatVes(item.saldo_usd) }})</span>
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
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
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
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-subtle);
}

thead {
  position: sticky;
  inset-block-start: 0;
  z-index: 2;
  background-color: var(--surface-subtle);
}

thead th:first-child {
  position: sticky;
  inset-inline-start: 0;
  z-index: 3;
  background-color: var(--surface-subtle);
}

th,
td {
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.85rem;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-subtle);
}

tbody th {
  position: sticky;
  inset-inline-start: 0;
  z-index: 1;
  background-color: var(--surface-card);
  font-weight: 700;
  color: var(--text-primary);
}

tbody tr.collection-row--own th,
tbody tr.collection-row--own td {
  background-color: var(--brand-tint);
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
  color: var(--brand-accent);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-pill);
  font-size: 0.75rem;
  font-weight: 700;
}

.status-pill--solvente,
.status-pill--pagado {
  background-color: var(--status-ok-bg);
  color: var(--status-ok-text);
}

.status-pill--abono_parcial,
.status-pill--pagado_parcial,
.status-pill--parcial {
  background-color: var(--status-warn-bg);
  color: var(--status-warn-text);
}

.status-pill--pendiente,
.status-pill--moroso,
.status-pill--vencido,
.status-pill--rechazado {
  background-color: var(--status-danger-bg);
  color: var(--status-danger-text);
}

.ves-subtext {
  display: inline-block;
  margin-left: 0.375rem;
  color: var(--text-secondary);
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
    display: none;
  }

  tbody tr {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  tbody th,
  tbody td {
    position: static;
    padding: 0.25rem 0;
    border-bottom: none;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
  }

  tbody td:nth-of-type(1)::before {
    content: var(--label-2);
    font-weight: 600;
    color: var(--text-secondary);
  }

  tbody td:nth-of-type(2)::before {
    content: var(--label-3);
    font-weight: 600;
    color: var(--text-secondary);
  }

  tbody td:nth-of-type(3)::before {
    content: var(--label-4);
    font-weight: 600;
    color: var(--text-secondary);
  }
}

.collection-table__empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 1.5rem 1rem;
}
</style>
