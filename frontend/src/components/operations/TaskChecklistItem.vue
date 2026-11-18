<script setup lang="ts">
import type { TareaDiariaDTO } from '../../stores/operationsStore';

withDefaults(
  defineProps<{
    task: TareaDiariaDTO;
    disabled?: boolean;
    canComplete?: boolean;
  }>(),
  {
    disabled: false,
    canComplete: true,
  },
);

const emit = defineEmits<{
  (e: 'complete', id: number): void;
}>();
</script>

<template>
  <article
    class="task-item selectable-card"
    :class="{ 'task-item--done is-selected': task.completada }"
    :aria-label="`Tarea operativa: ${task.titulo}`"
  >
    <label :for="`chk-task-${task.id}`" class="task-item__label">
      <input
        :id="`chk-task-${task.id}`"
        type="checkbox"
        class="task-item__checkbox visually-hidden"
        :checked="task.completada"
        :disabled="disabled || !canComplete || task.completada"
        @change="emit('complete', task.id)"
      />
      <span class="task-item__title">{{ task.titulo }}</span>
    </label>

    <div class="task-item__meta">
      <span class="task-item__area">Área: {{ task.area }}</span>
      <span v-if="task.incidencia_id" class="task-item__linked">
        Vinculada a incidencia vecinal
      </span>
      <span class="task-item__badge">
        {{ task.completada ? 'COMPLETADA' : 'PENDIENTE' }}
      </span>
    </div>
  </article>
</template>

<style scoped>
.task-item {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  color-scheme: light dark;
  accent-color: var(--brand-accent);
}

.task-item--done {
  background-color: var(--status-ok-bg);
  border-color: var(--status-ok-border);
}

.task-item__label {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  min-block-size: 2.75rem;
  cursor: pointer;
  font-weight: 600;
  color: var(--text-primary);
}

.task-item__checkbox {
  width: 22px;
  height: 22px;
  accent-color: var(--brand-accent);
  cursor: pointer;
}

.task-item--done .task-item__title {
  text-decoration: line-through;
  color: var(--status-ok-text);
  opacity: 0.85;
}

.task-item__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
}

.task-item__area {
  color: var(--text-secondary);
}

.task-item__linked {
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-pill);
  background-color: var(--brand-tint);
  color: var(--brand-accent);
  font-weight: 700;
}

.task-item__badge {
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-pill);
  background-color: var(--surface-subtle);
  color: var(--text-secondary);
  font-weight: 700;
}

@supports not (accent-color: oklch(0.44 0.14 235)) {
  .task-item__checkbox.visually-hidden {
    position: absolute !important;
    clip-path: inset(50%) !important;
    overflow: hidden !important;
    width: 1px !important;
    height: 1px !important;
    margin: -1px !important;
    padding: 0 !important;
    border: 0 !important;
    white-space: nowrap !important;
  }

  .task-item__label {
    position: relative;
    padding-left: 2rem;
  }

  .task-item__checkbox + span::before {
    content: '';
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 1.2rem;
    height: 1.2rem;
    border: 2px solid var(--border-control);
    background: var(--surface-card);
    border-radius: 4px;
    box-sizing: border-box;
  }

  .task-item__checkbox:checked + span::before {
    background-color: var(--brand-600);
    border-color: var(--brand-600);
  }
}
</style>
