<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useDualRefresh } from '../../composables/useDualRefresh';
import { useAuthStore } from '../../stores/authStore';
import { useFinanceStore } from '../../stores/financeStore';
import { useOperationsStore } from '../../stores/operationsStore';
import { isSafeRedirectUrl } from '../../utils/security';

const authStore = useAuthStore();
const financeStore = useFinanceStore();
const operationsStore = useOperationsStore();

const fecha = ref('2026-10-30');
const hora = ref('19:30');
const ubicacion = ref('Salón de Usos Múltiples');
const contenido = ref('');
const comunicadoTitulo = ref('');
const comunicadoContenido = ref('');
const comunicadoEnlace = ref('');
const statusBanner = ref<string | null>(null);

const canWriteSecretary = computed(() => {
  const rol = authStore.userRole;
  return rol === 'SECRETARIO' || rol === 'PRESIDENTE';
});

async function refreshLogbookData(): Promise<void> {
  await Promise.allSettled([
    operationsStore.fetchBitacora(),
    financeStore.fetchComunicadosRecientes(),
  ]);
}

const { isRefreshing, triggerRefresh } = useDualRefresh(refreshLogbookData);

onMounted(async () => {
  await refreshLogbookData();
});

async function handleSaveActa(): Promise<void> {
  statusBanner.value = null;
  if (contenido.value.trim().length < 5) {
    operationsStore.errorMessage = 'El contenido del acta debe tener al menos 5 caracteres.';
    return;
  }
  try {
    await operationsStore.crearActaBitacora({
      fecha: fecha.value,
      hora: hora.value,
      ubicacion: ubicacion.value.trim(),
      contenido: contenido.value.trim(),
    });
    contenido.value = '';
    statusBanner.value = 'Acta oficial registrada en la bitácora del condominio.';
  } catch {
    // Error almacenado en operationsStore.errorMessage
  }
}

async function handlePublishComunicado(): Promise<void> {
  statusBanner.value = null;
  operationsStore.errorMessage = null;
  financeStore.errorMessage = null;
  if (comunicadoTitulo.value.trim().length < 3 || comunicadoContenido.value.trim().length < 5) {
    operationsStore.errorMessage =
      'Indica un título (mín. 3 caracteres) y contenido oficial (mín. 5 caracteres).';
    return;
  }
  const enlaceTrimmed = comunicadoEnlace.value.trim();
  if (enlaceTrimmed && !enlaceTrimmed.startsWith('https://') && !isSafeRedirectUrl(enlaceTrimmed)) {
    operationsStore.errorMessage =
      'El enlace externo del comunicado debe ser una ruta interna o URL HTTPS segura.';
    return;
  }
  try {
    await financeStore.publicarComunicado({
      titulo: comunicadoTitulo.value.trim(),
      contenido: comunicadoContenido.value.trim(),
      enlace_externo: enlaceTrimmed || null,
    });
    comunicadoTitulo.value = '';
    comunicadoContenido.value = '';
    comunicadoEnlace.value = '';
    statusBanner.value = 'Comunicado oficial publicado en la cartelera vecinal.';
  } catch {
    // Error almacenado en financeStore.errorMessage
  }
}
</script>

<template>
  <section aria-labelledby="secretary-logbook-title">
    <header class="page-header">
      <div>
        <h1 id="secretary-logbook-title" class="page-header__title">
          Bitácora de Actas y Cartelera (Secretaría)
        </h1>
        <p class="page-header__subtitle">
          Registro cronológico de acuerdos de Junta, Asambleas de Propietarios y comunicados
          oficiales.
        </p>
      </div>
      <button
        id="btn-dual-refresh"
        type="button"
        class="dual-refresh-btn"
        :disabled="isRefreshing || operationsStore.isLoading || financeStore.isLoading"
        @click="triggerRefresh"
      >
        <span aria-hidden="true">🔄</span>
        <span>{{ isRefreshing ? 'Actualizando...' : 'Refrescar' }}</span>
      </button>
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

    <div v-if="canWriteSecretary" class="secretary-forms-grid">
      <form class="acta-form" @submit.prevent="handleSaveActa">
        <h2 class="section-subtitle">Asentar Nueva Acta en Bitácora</h2>
        <div class="inline-row">
          <div class="field-group">
            <label for="input-acta-fecha" class="field-label">Fecha</label>
            <input id="input-acta-fecha" v-model="fecha" type="date" required class="field-input" />
          </div>
          <div class="field-group">
            <label for="input-acta-hora" class="field-label">Hora</label>
            <input id="input-acta-hora" v-model="hora" type="text" required class="field-input" />
          </div>
        </div>

        <div class="field-group">
          <label for="input-acta-ubicacion" class="field-label">Ubicación de la sesión</label>
          <input
            id="input-acta-ubicacion"
            v-model="ubicacion"
            type="text"
            required
            class="field-input"
          />
        </div>

        <div class="field-group">
          <label for="input-acta-contenido" class="field-label">Acuerdos y puntos tratados</label>
          <textarea
            id="input-acta-contenido"
            v-model="contenido"
            rows="3"
            required
            class="field-input"
          />
        </div>

        <button id="btn-submit-acta" type="submit" class="btn-primary">
          Registrar Acta Oficial
        </button>
      </form>

      <form
        id="form-publicar-comunicado"
        class="acta-form"
        @submit.prevent="handlePublishComunicado"
      >
        <h2 class="section-subtitle">Publicar Comunicado Oficial en Cartelera</h2>
        <div class="field-group">
          <label for="input-comunicado-titulo" class="field-label">Título del comunicado</label>
          <input
            id="input-comunicado-titulo"
            v-model="comunicadoTitulo"
            type="text"
            required
            class="field-input"
          />
        </div>

        <div class="field-group">
          <label for="input-comunicado-contenido" class="field-label">Mensaje comunitario</label>
          <textarea
            id="input-comunicado-contenido"
            v-model="comunicadoContenido"
            rows="3"
            required
            class="field-input"
          />
        </div>

        <div class="field-group">
          <label for="input-comunicado-enlace" class="field-label">
            Enlace informativo opcional (HTTPS o ruta interna)
          </label>
          <input
            id="input-comunicado-enlace"
            v-model="comunicadoEnlace"
            type="text"
            class="field-input"
            placeholder="/consultas"
          />
        </div>

        <button id="btn-submit-comunicado" type="submit" class="btn-primary">
          Publicar Comunicado
        </button>
      </form>
    </div>

    <section aria-label="Historial cronológico de actas">
      <h2 class="section-title">Historial de Actas</h2>
      <p v-if="operationsStore.data.bitacora.length === 0" class="empty-state">
        No existen actas registradas en la bitácora.
      </p>
      <div v-else class="acta-list defer-feed-list">
        <article v-for="acta in operationsStore.data.bitacora" :key="acta.id" class="acta-card">
          <header class="acta-card__header">
            <strong>Acta oficial — {{ acta.fecha }} ({{ acta.hora }})</strong>
            <span class="acta-card__loc">{{ acta.ubicacion }}</span>
          </header>
          <p class="acta-card__content">{{ acta.contenido }}</p>
        </article>
      </div>
    </section>
  </section>
</template>

<style scoped>
.page-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.25rem;
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

.secretary-forms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.acta-form {
  padding: 1.25rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
}

.section-subtitle,
.section-title {
  margin: 0 0 0.75rem;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
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
  margin-bottom: 0.875rem;
}

.field-label {
  font-size: 0.85rem;
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

.acta-list {
  display: grid;
  gap: 0.875rem;
}

.acta-card {
  padding: 1rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
}

.acta-card__header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
  color: var(--text-primary);
}

.acta-card__loc {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.acta-card__content {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.empty-state {
  padding: 1.25rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}
</style>
