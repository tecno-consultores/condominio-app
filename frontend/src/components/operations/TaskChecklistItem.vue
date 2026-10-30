<script setup lang="ts">
import type { TareaDiariaDTO } from '../../stores/operationsStore';
import { sanitizeUntrustedText } from '../../utils/security';

defineProps<{
  task: TareaDiariaDTO;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: 'complete', id: number): void;
}>();
</script>

<template>
  <article
    class="task-item"
    :class="{ 'task-item--done': task.completada }"
    :aria-label="`Tarea #${task.id}: ${task.titulo}`"
  >
    <label :for="`chk-task-${task.id}`" class="task-item__label">
      <input
        :id="`chk-task-${task.id}`"
        type="checkbox"
        class="task-item__checkbox visually-hidden"
        :checked="task.completada"
        :disabled="disabled || task.completada"
        @change="emit('complete', task.id)"
      />
      <span class="task-item__title">{{ sanitizeUntrustedText(task.titulo) }}</span>
    </label>

    <div class="task-item__meta">
      <span class="task-item__area">Área: {{ sanitizeUntrustedText(task.area) }}</span>
      <span v-if="task.incidencia_id" class="task-item__linked">
        Cierra Incidencia #{{ task.incidencia_id }}
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
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  color-scheme: light dark;
  accent-color: #0284c7;
}

.task-item--done {
  background-color: #f0fdf4;
  border-color: #86efac;
}

.task-item__label {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  min-height: 44px;
  cursor: pointer;
  font-weight: 600;
  color: #0f172a;
}

.task-item__checkbox {
  width: 22px;
  height: 22px;
  accent-color: #0284c7;
  cursor: pointer;
}

.task-item--done .task-item__title {
  text-decoration: line-through;
  color: #166534;
}

.task-item__meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
}

.task-item__area {
  color: #475569;
}

.task-item__linked {
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
  background-color: #e0f2fe;
  color: #0369a1;
  font-weight: 700;
}

.task-item__badge {
  padding: 0.2rem 0.55rem;
  border-radius: 9999px;
  background-color: #f1f5f9;
  color: #334155;
  font-weight: 700;
}

@supports not (accent-color: #0284c7) {
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
    border: 2px solid #94a3b8;
    background: #ffffff;
    border-radius: 4px;
    box-sizing: border-box;
  }

  .task-item__checkbox:checked + span::before {
    background-color: #0284c7;
    border-color: #0284c7;
  }
}
</style>
