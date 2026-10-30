<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import TaskChecklistItem from '../../components/operations/TaskChecklistItem.vue';
import { useOperationsStore } from '../../stores/operationsStore';

const operationsStore = useOperationsStore();
const statusBanner = ref<string | null>(null);

const totalTasks = computed(() => operationsStore.data.tareasDiarias.length);
const completedTasks = computed(
  () => operationsStore.data.tareasDiarias.filter((t) => t.completada).length,
);

onMounted(async () => {
  await operationsStore.fetchTareasDiarias();
});

async function handleCompleteTask(tareaId: number): Promise<void> {
  statusBanner.value = null;
  try {
    const completed = await operationsStore.completarTareaDiaria(tareaId);
    statusBanner.value = completed.incidencia_id
      ? `Tarea #${tareaId} completada. Incidencia vinculada #${completed.incidencia_id} cerrada automáticamente.`
      : `Tarea #${tareaId} marcada como completada.`;
  } catch {
    // Error almacenado en operationsStore.errorMessage
  }
}
</script>

<template>
  <AppShellLayout>
    <header class="page-header">
      <div>
        <h1 class="page-header__title">Checklist Diario de Conserjería</h1>
        <p class="page-header__subtitle">
          Marca las labores realizadas hoy. Las tareas asociadas a una incidencia la cerrarán
          automáticamente.
        </p>
      </div>
      <div class="progress-box">
        <label for="tasks-progress-bar" class="progress-box__label">
          Progreso hoy: {{ completedTasks }} / {{ totalTasks }}
        </label>
        <progress
          id="tasks-progress-bar"
          class="progress-box__bar"
          :max="Math.max(1, totalTasks)"
          :value="completedTasks"
        >
          {{ completedTasks }} de {{ totalTasks }}
        </progress>
      </div>
    </header>

    <div v-if="operationsStore.errorMessage" class="banner banner--error" role="alert">
      {{ operationsStore.errorMessage }}
    </div>
    <div v-if="statusBanner" class="banner banner--success" role="status">
      {{ statusBanner }}
    </div>

    <section aria-label="Lista de tareas operativas del día">
      <p v-if="totalTasks === 0" class="empty-state">
        No hay tareas asignadas para la jornada de hoy.
      </p>
      <div v-else class="tasks-list">
        <TaskChecklistItem
          v-for="task in operationsStore.data.tareasDiarias"
          :key="task.id"
          :task="task"
          :disabled="operationsStore.isLoading"
          @complete="handleCompleteTask"
        />
      </div>
    </section>
  </AppShellLayout>
</template>

<style scoped>
.page-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.25rem;
  color-scheme: light dark;
  accent-color: #0284c7;
}

.page-header__title {
  margin: 0;
  font-size: 1.3rem;
  color: #0f172a;
}

.page-header__subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: #475569;
}

.progress-box {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 180px;
}

.progress-box__label {
  font-size: 0.825rem;
  font-weight: 700;
  color: #0f172a;
}

.progress-box__bar {
  width: 100%;
  height: 12px;
  accent-color: #0284c7;
}

.banner {
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.banner--error {
  background-color: #fef2f2;
  border: 1px solid #f87171;
  color: #991b1b;
}

.banner--success {
  background-color: #f0fdf4;
  border: 1px solid #4ade80;
  color: #166534;
}

.tasks-list {
  display: grid;
  gap: 0.75rem;
}

.empty-state {
  padding: 1.25rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
}
</style>
