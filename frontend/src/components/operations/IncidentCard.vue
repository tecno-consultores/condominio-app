<script setup lang="ts">
import { computed, ref } from 'vue';
import type { IncidenciaDTO } from '../../stores/operationsStore';
import { isSafeMediaUrl } from '../../utils/security';

const props = defineProps<{
  incident: IncidenciaDTO;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: 'adherir', id: number): void;
}>();

const isPulsing = ref(false);
const safeImageUrl = computed<string | null>(() => {
  if (!props.incident.url_foto || !isSafeMediaUrl(props.incident.url_foto)) {
    return null;
  }
  return props.incident.url_foto.trim();
});

const isProcessingEvidence = computed<boolean>(() =>
  Boolean(props.incident.url_foto && props.incident.url_foto.trim().startsWith('s3://')),
);

function handleAdherir(): void {
  isPulsing.value = true;
  setTimeout(() => {
    isPulsing.value = false;
  }, 350);
  emit('adherir', props.incident.id);
}
</script>

<template>
  <article class="incident-card" :aria-label="`Incidencia vecinal en ${incident.area}`">
    <header class="incident-card__header">
      <div>
        <strong class="incident-card__area">{{ incident.area }}</strong>
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

    <p class="incident-card__desc">{{ incident.descripcion }}</p>

    <figure v-if="safeImageUrl" class="incident-card__media">
      <img
        :src="safeImageUrl"
        :alt="`Fotografía de evidencia en ${incident.area}`"
        class="incident-card__img"
        loading="lazy"
        decoding="async"
        width="320"
        height="180"
      />
    </figure>

    <footer class="incident-card__footer">
      <span v-if="isProcessingEvidence" class="avif-badge">Evidencia AVIF en procesamiento</span>
      <span v-else-if="safeImageUrl" class="avif-badge">Evidencia fotográfica adjunta</span>
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
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
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
  color: var(--text-primary);
  margin-right: 0.5rem;
}

.incident-card__status {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-pill);
  font-size: 0.725rem;
  font-weight: 700;
}

.incident-card__status--abierto {
  background-color: var(--status-danger-bg);
  color: var(--status-danger-text);
}

.incident-card__status--en_proceso {
  background-color: var(--status-warn-bg);
  color: var(--status-warn-text);
}

.incident-card__status--cerrado {
  background-color: var(--status-ok-bg);
  color: var(--status-ok-text);
}

.incident-card__counter {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--status-warn-text);
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
  color: var(--text-secondary);
}

.incident-card__media {
  margin: 0 0 0.875rem;
}

.incident-card__img {
  display: block;
  max-inline-size: 100%;
  block-size: auto;
  max-block-size: 14rem;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
}

.incident-card__footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.avif-badge {
  font-size: 0.75rem;
  color: var(--brand-accent);
  font-weight: 600;
}

.btn-me-sumo {
  min-block-size: 2.75rem;
  margin-left: auto;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--brand-accent);
  background-color: var(--brand-tint);
  color: var(--brand-accent);
  font-weight: 700;
  cursor: pointer;
}

.btn-me-sumo:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
