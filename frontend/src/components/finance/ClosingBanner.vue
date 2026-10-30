<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    dayOfMonth?: number;
    isClosed?: boolean;
    periodo?: string;
  }>(),
  {
    dayOfMonth: () => new Date().getDate(),
    isClosed: false,
    periodo: '2026-10',
  },
);

const shouldRender = computed(
  () => props.isClosed || (props.dayOfMonth >= 1 && props.dayOfMonth <= 10),
);
</script>

<template>
  <aside
    v-if="shouldRender"
    id="closing-banner"
    class="closing-banner"
    :class="{ 'closing-banner--locked': isClosed }"
    role="status"
    aria-live="polite"
  >
    <div class="closing-banner__content">
      <strong class="closing-banner__title">
        {{
          isClosed
            ? `Candado Contable Activo (${periodo})`
            : `Ventana de Cierre Mensual (${periodo})`
        }}
      </strong>
      <p class="closing-banner__text">
        {{
          isClosed
            ? 'Este periodo contable se encuentra cerrado e inmutable. Los nuevos pagos se imputarán al periodo en curso.'
            : 'Del día 1 al 10 de cada mes la Tesorería concilia abonos antes de activar el Candado Contable.'
        }}
      </p>
    </div>
  </aside>
</template>

<style scoped>
.closing-banner {
  padding: 0.875rem 1rem;
  margin-bottom: 1.25rem;
  border-radius: 0.75rem;
  background-color: #eff6ff;
  border: 1px solid #93c5fd;
  color: #1e3a8a;
}

.closing-banner--locked {
  background-color: #fef3c7;
  border-color: #f59e0b;
  color: #78350f;
}

.closing-banner__title {
  display: block;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.closing-banner__text {
  margin: 0;
  font-size: 0.825rem;
}
</style>
