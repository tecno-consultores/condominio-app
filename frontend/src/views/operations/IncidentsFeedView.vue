<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import EmptyStateCard from '../../components/common/EmptyStateCard.vue';
import SkeletonCard from '../../components/common/SkeletonCard.vue';
import IncidentCard from '../../components/operations/IncidentCard.vue';
import { useDualRefresh } from '../../composables/useDualRefresh';
import { useIdempotency } from '../../composables/useIdempotency';
import { useFinanceStore } from '../../stores/financeStore';
import { useOperationsStore } from '../../stores/operationsStore';
import { validateProofFileUpload } from '../../utils/security';

const financeStore = useFinanceStore();
const operationsStore = useOperationsStore();
const { isSubmitting, executeWithIdempotency } = useIdempotency();

const showNewForm = ref(false);
const area = ref('Bombas de Agua');
const descripcion = ref('');
const selectedFile = ref<File | null>(null);
const selectedFileName = ref<string | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);
const statusBanner = ref<string | null>(null);

const { isRefreshing, triggerRefresh } = useDualRefresh(() => operationsStore.fetchIncidencias());

onMounted(async () => {
  await operationsStore.fetchIncidencias();
});

function handleEvidenceChange(event: Event): void {
  operationsStore.errorMessage = null;
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    selectedFile.value = null;
    selectedFileName.value = null;
    return;
  }
  const check = validateProofFileUpload({ name: file.name, size: file.size, type: file.type });
  if (!check.valid) {
    operationsStore.errorMessage = check.error ?? 'Archivo de evidencia inválido.';
    selectedFile.value = null;
    selectedFileName.value = null;
    input.value = '';
    return;
  }
  selectedFile.value = file;
  selectedFileName.value = file.name;
}

async function handleCreateIncident(): Promise<void> {
  statusBanner.value = null;
  if (descripcion.value.trim().length < 5) {
    operationsStore.errorMessage = 'Describe la falla con al menos 5 caracteres.';
    return;
  }
  try {
    await executeWithIdempotency(async (key) => {
      let uploadedUrl: string | null = null;
      if (selectedFile.value) {
        const upload = await financeStore.subirEvidencia(selectedFile.value, 'incidencias');
        uploadedUrl = upload.url;
      }
      await operationsStore.crearIncidencia(
        {
          area: area.value,
          descripcion: descripcion.value.trim(),
          url_foto: uploadedUrl,
        },
        key,
      );
    });
    descripcion.value = '';
    selectedFile.value = null;
    selectedFileName.value = null;
    if (fileInputRef.value) {
      fileInputRef.value.value = '';
    }
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
    statusBanner.value =
      'Te sumaste a la incidencia reportada. Prioridad comunitaria incrementada.';
  } catch {
    // Error almacenado en operationsStore.errorMessage
  }
}
</script>

<template>
  <section aria-labelledby="incidents-page-title">
    <header class="page-header">
      <div>
        <h1 id="incidents-page-title" class="page-header__title">
          Embudo Comunitario de Incidencias ("¡Me sumo!")
        </h1>
        <p class="page-header__subtitle">
          Súmate a un reporte existente para evitar duplicados o registra una falla nueva.
        </p>
      </div>
      <div class="page-header__actions">
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
        <button
          id="btn-open-new-incident"
          type="button"
          class="btn-primary"
          :aria-expanded="showNewForm ? 'true' : 'false'"
          aria-controls="new-incident-panel"
          @click="showNewForm = !showNewForm"
        >
          {{ showNewForm ? 'Cerrar Formulario' : 'Reportar Nueva Falla' }}
        </button>
      </div>
    </header>

    <div v-if="operationsStore.errorMessage" class="banner banner--error" role="alert">
      {{ operationsStore.errorMessage }}
    </div>
    <div v-if="financeStore.errorMessage" class="banner banner--error" role="alert">
      {{ financeStore.errorMessage }}
    </div>
    <div v-if="statusBanner" class="banner banner--success" role="status">
      {{ statusBanner }}
    </div>

    <div
      id="new-incident-panel"
      class="collapsible-panel"
      :data-expanded="showNewForm ? 'true' : 'false'"
    >
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

        <div class="field-group">
          <label for="input-inc-evidencia" class="field-label">
            Fotografía o evidencia opcional (JPG, PNG, WEBP, AVIF o PDF — máx. 2 MB)
          </label>
          <input
            id="input-inc-evidencia"
            ref="fileInputRef"
            type="file"
            accept="image/jpeg,image/png,image/webp,image/avif,application/pdf"
            class="field-input"
            @change="handleEvidenceChange"
          />
          <p v-if="selectedFileName" class="field-hint">
            Evidencia validada: {{ selectedFileName }}
          </p>
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
    </div>

    <section aria-label="Incidencias activas por prioridad">
      <SkeletonCard
        v-if="operationsStore.isLoading && operationsStore.data.incidencias.length === 0"
        :lines="3"
        height="120px"
        label="Cargando incidencias abiertas..."
      />
      <EmptyStateCard
        v-else-if="operationsStore.data.incidencias.length === 0"
        class="empty-state"
        title="Todo en orden en la comunidad"
        description="No hay incidencias abiertas en el condominio."
        icon="check"
        action-label="Reportar Nueva Falla"
        @action="showNewForm = true"
      />
      <div v-else class="incident-list defer-feed-list">
        <IncidentCard
          v-for="inc in operationsStore.data.incidencias"
          :key="inc.id"
          :incident="inc"
          :disabled="operationsStore.isLoading"
          @adherir="handleAdherir"
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
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.625rem;
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

.incident-form {
  padding: 1.25rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
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
  color: var(--text-primary);
}

.field-hint {
  margin: 0;
  font-size: 0.775rem;
  color: var(--text-secondary);
}

.field-input {
  min-block-size: 2.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-card);
  color: var(--text-primary);
  font-size: 0.95rem;
}

.incident-list {
  display: grid;
  gap: 0.875rem;
}

.empty-state {
  padding: 1.25rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

.btn-primary {
  min-block-size: 2.75rem;
  padding: 0.625rem 1rem;
  border-radius: var(--radius-sm);
  border: none;
  background-color: var(--brand-600);
  color: var(--text-on-accent);
  font-weight: 700;
  cursor: pointer;
}
</style>
