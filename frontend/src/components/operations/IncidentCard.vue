<script setup lang="ts">
import type { IncidenciaDTO } from '../../stores/operationsStore';
import { sanitizeUntrustedText } from '../../utils/security';

defineProps<{
  incident: IncidenciaDTO;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: 'adherir', id: number): void;
}>();
</script>

<template>
  <article class="incident-card" :aria-label="`Incidencia #${incident.id} en ${incident.area}`">
    <header class="incident-card__header">
      <div>
        <strong class="incident-card__area">{{ sanitizeUntrustedText(incident.area) }}</strong>
        <span
          class="incident-card__status"
          :class="`incident-card__status--${incident.estado.toLowerCase()}`"
        >
          {{ incident.estado }}
        </span>
      </div>
      <span class="incident-card__counter">🔥 {{ incident.adhesiones_count }} vecinos</span>
    </header>

    <p class="incident-card__desc">{{ sanitizeUntrustedText(incident.descripcion) }}</p>

    <footer class="incident-card__footer">
      <span v-if="incident.url_foto" class="avif-badge">Evidencia AVIF optimizada</span>
      <button
        type="button"
        class="btn-me-sumo"
        :disabled="disabled || incident.estado === 'CERRADO'"
        @click="emit('adherir', incident.id)"
      >
        ¡Me sumo! (+1 prioridad)
      </button>
    </footer>
  </article>
</template>

<style scoped>
.incident-card {
  padding: 1.125rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
}

.incident-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.incident-card__area {
  font-size: 1rem;
  color: #0f172a;
  margin-right: 0.5rem;
}

.incident-card__status {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.725rem;
  font-weight: 700;
}

.incident-card__status--abierto {
  background-color: #fee2e2;
  color: #991b1b;
}

.incident-card__status--en_proceso {
  background-color: #fef3c7;
  color: #92400e;
}

.incident-card__status--cerrado {
  background-color: #dcfce7;
  color: #166534;
}

.incident-card__counter {
  font-size: 0.85rem;
  font-weight: 700;
  color: #ea580c;
}

.incident-card__desc {
  margin: 0 0 0.875rem;
  font-size: 0.9rem;
  color: #334155;
}

.incident-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.avif-badge {
  font-size: 0.75rem;
  color: #0284c7;
  font-weight: 600;
}

.btn-me-sumo {
  min-height: 44px;
  margin-left: auto;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #0284c7;
  background-color: #f0f9ff;
  color: #0369a1;
  font-weight: 700;
  cursor: pointer;
}

.btn-me-sumo:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
