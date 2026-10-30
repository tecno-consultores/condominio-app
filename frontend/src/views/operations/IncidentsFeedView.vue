<script setup lang="ts">
import { onMounted, ref } from 'vue';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import IncidentCard from '../../components/operations/IncidentCard.vue';
import { useIdempotency } from '../../composables/useIdempotency';
import { useOperationsStore } from '../../stores/operationsStore';

const operationsStore = useOperationsStore();
const { isSubmitting, executeWithIdempotency } = useIdempotency();

const showNewForm = ref(false);
const area = ref('Bombas de Agua');
const descripcion = ref('');
const statusBanner = ref<string | null>(null);

onMounted(async () => {
  await operationsStore.fetchIncidencias();
});

async function handleCreateIncident(): Promise<void> {
  statusBanner.value = null;
  if (descripcion.value.trim().length < 5) {
    operationsStore.errorMessage = 'Describe la falla con al menos 5 caracteres.';
    return;
  }
  try {
    await executeWithIdempotency(async (key) => {
      await operationsStore.crearIncidencia(
        {
          area: area.value,
          descripcion: descripcion.value.trim(),
        },
        key,
      );
    });
    descripcion.value = '';
    showNewForm.value = false;
    statusBanner.value = 'Incidencia reportada y notificada a la Junta de Condominio.';
  } catch {
    // Error almacenado en operationsStore.errorMessage
  }
}

async function handleAdherir(incidenciaId: number): Promise<void> {
  statusBanner.value = null;
  try {
    await operationsStore.adherirIncidencia(incidenciaId);
    statusBanner.value = `Te sumaste a la incidencia #${incidenciaId}. Prioridad comunitaria incrementada.`;
  } catch {
    // Error almacenado en operationsStore.errorMessage
  }
}
</script>

<template>
  <AppShellLayout>
    <header class="page-header">
      <div>
        <h1 class="page-header__title">Embudo Comunitario de Incidencias ("¡Me sumo!")</h1>
        <p class="page-header__subtitle">
          Súmate a un reporte existente para evitar duplicados o registra una falla nueva.
        </p>
      </div>
      <button
        id="btn-open-new-incident"
        type="button"
        class="btn-primary"
        @click="showNewForm = !showNewForm"
      >
        {{ showNewForm ? 'Cerrar Formulario' : 'Reportar Nueva Falla' }}
      </button>
    </header>

    <div v-if="operationsStore.errorMessage" class="banner banner--error" role="alert">
      {{ operationsStore.errorMessage }}
    </div>
    <div v-if="statusBanner" class="banner banner--success" role="status">
      {{ statusBanner }}
    </div>

    <form
      v-if="showNewForm"
      id="new-incident-form"
      class="incident-form"
      @submit.prevent="handleCreateIncident"
    >
      <div class="field-group">
        <label for="input-inc-area" class="field-label">Área afectada</label>
        <select id="input-inc-area" v-model="area" class="field-input">
          <option value="Bombas de Agua">Bombas de Agua</option>
          <option value="Ascensores">Ascensores</option>
          <option value="Portón Eléctrico">Portón Eléctrico</option>
          <option value="Iluminación y Pasillos">Iluminación y Pasillos</option>
        </select>
      </div>

      <div class="field-group">
        <label for="input-inc-descripcion" class="field-label">Descripción detallada</label>
        <p id="inc-desc-hint" class="field-hint">
          Mínimo 5 caracteres indicando piso, torre o síntoma observado.
        </p>
        <textarea
          id="input-inc-descripcion"
          v-model="descripcion"
          rows="3"
          required
          minlength="5"
          aria-describedby="inc-desc-hint"
          class="field-input"
        />
      </div>

      <button
        id="btn-submit-incident"
        type="submit"
        class="btn-primary"
        :disabled="isSubmitting"
        :aria-busy="isSubmitting ? 'true' : 'false'"
      >
        Publicar Incidencia
      </button>
    </form>

    <section aria-label="Incidencias activas por prioridad">
      <p v-if="operationsStore.data.incidencias.length === 0" class="empty-state">
        No hay incidencias abiertas en el condominio.
      </p>
      <div v-else class="incident-list">
        <IncidentCard
          v-for="inc in operationsStore.data.incidencias"
          :key="inc.id"
          :incident="inc"
          :disabled="operationsStore.isLoading"
          @adherir="handleAdherir"
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

.incident-form {
  padding: 1.25rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  margin-bottom: 1.25rem;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 1rem;
}

.field-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #1e293b;
}

.field-hint {
  margin: 0;
  font-size: 0.775rem;
  color: #475569;
}

.field-input {
  min-height: 44px;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  font-size: 0.95rem;
}

.incident-list {
  display: grid;
  gap: 0.875rem;
}

.empty-state {
  padding: 1.25rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
}

.btn-primary {
  min-height: 44px;
  padding: 0.625rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background-color: #0284c7;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}
</style>
