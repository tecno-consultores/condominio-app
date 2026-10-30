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
              {{ item.estado }}
            </span>
          </td>
          <td>
            <strong>{{ item.saldo_usd }} USD</strong>
            <span class="ves-subtext">({{ formatVes(item.saldo_usd) }} VES)</span>
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
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 0.75rem;
  box-shadow:
    0 1px 3px 0 rgba(15, 23, 42, 0.06),
    0 1px 2px -1px rgba(15, 23, 42, 0.06);
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
  color: #0f172a;
  border-bottom: 1px solid #e2e8f0;
}

thead {
  position: sticky;
  inset-block-start: 0;
  z-index: 1;
  background-color: #f8fafc;
}

th,
td {
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.85rem;
  border-bottom: 1px solid #f1f5f9;
}

tbody th {
  position: sticky;
  inset-inline-start: 0;
  background-color: #ffffff;
  font-weight: 700;
  color: #0f172a;
}

.collection-row--own tbody th,
.collection-row--own td {
  background-color: #f0f9ff;
}

.own-badge {
  margin-left: 0.375rem;
  font-size: 0.75rem;
  color: #0284c7;
}

.status-pill {
  display: inline-block;
  padding: 0.2rem 0.55rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 700;
}

.status-pill--solvente {
  background-color: #dcfce7;
  color: #166534;
}

.status-pill--abono_parcial {
  background-color: #fef3c7;
  color: #92400e;
}

.status-pill--pendiente,
.status-pill--moroso {
  background-color: #fee2e2;
  color: #991b1b;
}

.ves-subtext {
  display: inline-block;
  margin-left: 0.375rem;
  color: #475569;
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
    border: 1px solid #cbd5e1;
    border-radius: 0.5rem;
  }

  tbody th {
    position: sticky;
    inset-block-start: 0;
    z-index: 2;
    background-color: #f1f5f9;
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
