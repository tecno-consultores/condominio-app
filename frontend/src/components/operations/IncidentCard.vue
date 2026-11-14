<script setup lang="ts">
import { ref } from 'vue';
import type { IncidenciaDTO } from '../../stores/operationsStore';
import { sanitizeUntrustedText } from '../../utils/security';

const props = defineProps<{
  incident: IncidenciaDTO;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: 'adherir', id: number): void;
}>();

const isPulsing = ref(false);

function handleAdherir(): void {
  isPulsing.value = true;
  setTimeout(() => {
    isPulsing.value = false;
  }, 350);
  emit('adherir', props.incident.id);
}
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
      <span
        class="incident-card__counter tabular-nums"
        :class="{ 'incident-card__counter--pulse': isPulsing }"
      >
        🔥 {{ incident.adhesiones_count }} vecinos
      </span>
    </header>

    <p class="incident-card__desc">{{ sanitizeUntrustedText(incident.descripcion) }}</p>

    <footer class="incident-card__footer">
      <span v-if="incident.url_foto" class="avif-badge">Evidencia AVIF optimizada</span>
      <button
        type="button"
        class="btn-me-sumo"
        :disabled="disabled || incident.estado === 'CERRADO'"
        @click="handleAdherir"
      >
        ¡Me sumo! (+1 prioridad)
      </button>
    </footer>
  </article>
</template>

<style scoped>
.incident-card {
  padding: 1.125rem;
  border-radius: var(--radius-md, 0.75rem);
  background-color: var(--surface-card, #ffffff);
  border: 1px solid var(--border-subtle, #cbd5e1);
  box-shadow: var(--shadow-card);
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
  color: var(--text-primary, #0f172a);
  margin-right: 0.5rem;
}

.incident-card__status {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-pill, 9999px);
  font-size: 0.725rem;
  font-weight: 700;
}

.incident-card__status--abierto {
  background-color: var(--status-danger-bg, #fee2e2);
  color: var(--status-danger-text, #991b1b);
}

.incident-card__status--en_proceso {
  background-color: var(--status-warn-bg, #fef3c7);
  color: var(--status-warn-text, #92400e);
}

.incident-card__status--cerrado {
  background-color: var(--status-ok-bg, #dcfce7);
  color: var(--status-ok-text, #166534);
}

.incident-card__counter {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--status-warn-text, #92400e);
}

@media (prefers-reduced-motion: no-preference) {
  .incident-card__counter--pulse {
    animation: support-pulse 0.35s cubic-bezier(0.2, 0, 0, 1);
  }

  @keyframes support-pulse {
    0% {
      transform: scale(1);
    }
    50% {
      transform: scale(1.1);
    }
    100% {
      transform: scale(1);
    }
  }
}

.incident-card__desc {
  margin: 0 0 0.875rem;
  font-size: 0.9rem;
  color: var(--text-secondary, #334155);
}

.incident-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.avif-badge {
  font-size: 0.75rem;
  color: var(--brand-accent, #0369a1);
  font-weight: 600;
}

.btn-me-sumo {
  min-height: 44px;
  margin-left: auto;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm, 0.5rem);
  border: 1px solid var(--brand-accent, #0369a1);
  background-color: var(--brand-tint, #f0f9ff);
  color: var(--brand-accent, #0369a1);
  font-weight: 700;
  cursor: pointer;
}

.btn-me-sumo:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
