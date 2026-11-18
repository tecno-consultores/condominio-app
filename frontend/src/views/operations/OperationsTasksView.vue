<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import EmptyStateCard from '../../components/common/EmptyStateCard.vue';
import SkeletonCard from '../../components/common/SkeletonCard.vue';
import TaskChecklistItem from '../../components/operations/TaskChecklistItem.vue';
import { useDualRefresh } from '../../composables/useDualRefresh';
import { useAuthStore } from '../../stores/authStore';
import { useOperationsStore, type FrecuenciaTarea } from '../../stores/operationsStore';

const authStore = useAuthStore();
const operationsStore = useOperationsStore();

const statusBanner = ref<string | null>(null);
const plantillaTitulo = ref('');
const plantillaArea = ref('Acceso Principal');
const plantillaFrecuencia = ref<FrecuenciaTarea>('DIARIA');
const tareaTitulo = ref('');
const tareaArea = ref('Bombas de Agua');

const canCompleteTasks = computed(() => {
  const rol = authStore.userRole;
  return rol === 'CONSERJE' || rol === 'PRESIDENTE' || rol === 'VICEPRESIDENTE';
});

const canManageTasks = computed(() => {
  const rol = authStore.userRole;
  return rol === 'PRESIDENTE' || rol === 'VICEPRESIDENTE';
});

const totalTasks = computed(() => operationsStore.data.tareasDiarias.length);
const completedTasks = computed(
  () => operationsStore.data.tareasDiarias.filter((t) => t.completada).length,
);

const { isRefreshing, triggerRefresh } = useDualRefresh(() => operationsStore.fetchTareasDiarias());

onMounted(async () => {
  await operationsStore.fetchTareasDiarias();
});

async function handleCompleteTask(tareaId: number): Promise<void> {
  statusBanner.value = null;
  if (!canCompleteTasks.value) {
    operationsStore.errorMessage = 'Solo Conserjería o Directiva puede completar tareas.';
    return;
  }
  try {
    const completed = await operationsStore.completarTareaDiaria(tareaId);
    statusBanner.value = completed.incidencia_id
      ? 'Tarea completada. La incidencia vinculada fue cerrada automáticamente.'
      : 'Tarea marcada como completada.';
  } catch {
    // Error almacenado en operationsStore.errorMessage
  }
}

async function handleCreatePlantilla(): Promise<void> {
  statusBanner.value = null;
  if (plantillaTitulo.value.trim().length < 3) {
    operationsStore.errorMessage = 'Indica un título de al menos 3 caracteres para la plantilla.';
    return;
  }
  try {
    const created = await operationsStore.crearPlantillaTarea({
      titulo: plantillaTitulo.value.trim(),
      area: plantillaArea.value.trim(),
      frecuencia: plantillaFrecuencia.value,
    });
    plantillaTitulo.value = '';
    statusBanner.value = `Plantilla periódica "${created.titulo}" creada.`;
  } catch {
    // Error almacenado en operationsStore.errorMessage
  }
}

async function handleCreateDailyTask(): Promise<void> {
  statusBanner.value = null;
  if (tareaTitulo.value.trim().length < 3) {
    operationsStore.errorMessage = 'Indica un título de al menos 3 caracteres para la tarea.';
    return;
  }
  try {
    await operationsStore.crearTareaDiaria({
      titulo: tareaTitulo.value.trim(),
      area: tareaArea.value.trim(),
    });
    tareaTitulo.value = '';
    statusBanner.value = 'Tarea operativa asignada a la jornada actual.';
  } catch {
    // Error almacenado en operationsStore.errorMessage
  }
}

async function handleGenerateDailyTasks(): Promise<void> {
  statusBanner.value = null;
  try {
    const res = await operationsStore.generarTareasDiarias();
    await operationsStore.fetchTareasDiarias();
    statusBanner.value = `Generación automática completada (${res.tareas_generadas} tareas nuevas).`;
  } catch {
    // Error almacenado en operationsStore.errorMessage
  }
}
</script>

<template>
  <section aria-labelledby="tasks-page-title">
    <header class="page-header">
      <div>
        <h1 id="tasks-page-title" class="page-header__title">Checklist Diario de Conserjería</h1>
        <p class="page-header__subtitle">
          Marca las labores realizadas hoy. Las tareas asociadas a una incidencia la cerrarán
          automáticamente.
        </p>
      </div>
      <div class="page-header__right">
        <button
          id="btn-dual-refresh"
          type="button"
          class="dual-refresh-btn"
          :disabled="isRefreshing || operationsStore.isLoading"
          @click="triggerRefresh"
        >
          <span aria-hidden="true">🔄</span>
          <span>{{ isRefreshing ? 'Actualizando...' : 'Refrescar' }}</span>
        </button>
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
      </div>
    </header>

    <div v-if="operationsStore.errorMessage" class="banner banner--error" role="alert">
      {{ operationsStore.errorMessage }}
    </div>
    <div v-if="statusBanner" class="banner banner--success" role="status">
      {{ statusBanner }}
    </div>

    <section
      v-if="canManageTasks"
      id="directive-tasks-panel"
      class="management-grid"
      aria-label="Gestión directiva de rutinas y tareas"
    >
      <form
        id="form-crear-plantilla"
        class="management-card"
        @submit.prevent="handleCreatePlantilla"
      >
        <h2 class="management-card__title">Nueva Plantilla Periódica</h2>
        <div class="field-group">
          <label for="input-plantilla-titulo" class="field-label">Título de rutina</label>
          <input
            id="input-plantilla-titulo"
            v-model="plantillaTitulo"
            type="text"
            required
            class="field-input"
          />
        </div>
        <div class="inline-row">
          <div class="field-group">
            <label for="input-plantilla-area" class="field-label">Área</label>
            <input
              id="input-plantilla-area"
              v-model="plantillaArea"
              type="text"
              required
              class="field-input"
            />
          </div>
          <div class="field-group">
            <label for="select-plantilla-frecuencia" class="field-label">Frecuencia</label>
            <select
              id="select-plantilla-frecuencia"
              v-model="plantillaFrecuencia"
              class="field-input"
            >
              <option value="DIARIA">DIARIA</option>
              <option value="SEMANAL">SEMANAL</option>
              <option value="MENSUAL">MENSUAL</option>
            </select>
          </div>
        </div>
        <div class="management-card__actions">
          <button id="btn-submit-plantilla" type="submit" class="btn-primary">
            Guardar Plantilla
          </button>
          <button
            id="btn-generar-tareas-diarias"
            type="button"
            class="btn-secondary"
            :disabled="operationsStore.isLoading"
            @click="handleGenerateDailyTasks"
          >
            Generar Tareas de Hoy
          </button>
        </div>
      </form>

      <form
        id="form-crear-tarea-diaria"
        class="management-card"
        @submit.prevent="handleCreateDailyTask"
      >
        <h2 class="management-card__title">Asignar Tarea Puntual</h2>
        <div class="field-group">
          <label for="input-tarea-titulo" class="field-label">Descripción de labor</label>
          <input
            id="input-tarea-titulo"
            v-model="tareaTitulo"
            type="text"
            required
            class="field-input"
          />
        </div>
        <div class="field-group">
          <label for="input-tarea-area" class="field-label">Área</label>
          <input
            id="input-tarea-area"
            v-model="tareaArea"
            type="text"
            required
            class="field-input"
          />
        </div>
        <button id="btn-submit-tarea-diaria" type="submit" class="btn-primary">
          Asignar a Conserjería
        </button>
      </form>
    </section>

    <section aria-label="Lista de tareas operativas del día">
      <SkeletonCard
        v-if="operationsStore.isLoading && totalTasks === 0"
        :lines="3"
        height="120px"
        label="Cargando tareas de hoy..."
      />
      <EmptyStateCard
        v-else-if="totalTasks === 0"
        class="empty-state"
        title="Jornada operativa libre"
        description="No hay tareas asignadas para la jornada de hoy."
        icon="check"
      />
      <div v-else class="tasks-list">
        <TaskChecklistItem
          v-for="task in operationsStore.data.tareasDiarias"
          :key="task.id"
          :task="task"
          :disabled="operationsStore.isLoading"
          :can-complete="canCompleteTasks"
          @complete="handleCompleteTask"
        />
      </div>
    </section>
  </section>
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
  accent-color: var(--brand-600);
}

.page-header__right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
}

.page-header__title {
  margin: 0;
  font-size: 1.3rem;
  color: var(--text-primary);
}

.page-header__subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: var(--text-secondary);
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
  color: var(--text-primary);
}

.progress-box__bar {
  width: 100%;
  height: 12px;
  accent-color: var(--brand-600);
}

.banner {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-sm);
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.banner--error {
  background-color: var(--status-danger-bg);
  border: 1px solid var(--status-danger-border);
  color: var(--status-danger-text);
}

.banner--success {
  background-color: var(--status-ok-bg);
  border: 1px solid var(--status-ok-border);
  color: var(--status-ok-text);
}

.management-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.management-card {
  padding: 1rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.management-card__title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
}

.management-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.625rem;
}

.inline-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.field-group {
  flex: 1 1 8rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.field-label {
  font-size: 0.825rem;
  font-weight: 600;
  color: var(--text-primary);
}

.field-input {
  min-block-size: 2.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-card);
  color: var(--text-primary);
  font-size: 0.9rem;
}

.btn-primary,
.btn-secondary {
  min-block-size: 2.75rem;
  padding: 0.55rem 1rem;
  border-radius: var(--radius-sm);
  font-weight: 700;
  cursor: pointer;
}

.btn-primary {
  border: none;
  background-color: var(--brand-600);
  color: var(--text-on-accent);
}

.btn-secondary {
  border: 1px solid var(--border-control);
  background-color: var(--surface-subtle);
  color: var(--text-primary);
}

.tasks-list {
  display: grid;
  gap: 0.75rem;
}

.empty-state {
  padding: 1.25rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}
</style>
