<script setup lang="ts">
import { onMounted, ref } from 'vue';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import { useOperationsStore } from '../../stores/operationsStore';
import { sanitizeUntrustedText } from '../../utils/security';

const operationsStore = useOperationsStore();

const fecha = ref('2026-10-30');
const hora = ref('19:30');
const ubicacion = ref('Salón de Usos Múltiples');
const contenido = ref('');
const statusBanner = ref<string | null>(null);

onMounted(async () => {
  await operationsStore.fetchBitacora();
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
</script>

<template>
  <AppShellLayout>
    <header class="page-header">
      <h1 class="page-header__title">Bitácora de Actas y Minutas (Secretaría)</h1>
      <p class="page-header__subtitle">
        Registro cronológico de acuerdos de Junta y Asambleas de Propietarios.
      </p>
    </header>

    <div v-if="operationsStore.errorMessage" class="banner banner--error" role="alert">
      {{ operationsStore.errorMessage }}
    </div>
    <div v-if="statusBanner" class="banner banner--success" role="status">
      {{ statusBanner }}
    </div>

    <form class="acta-form" @submit.prevent="handleSaveActa">
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

      <button id="btn-submit-acta" type="submit" class="btn-primary">Registrar Acta Oficial</button>
    </form>

    <section aria-label="Historial cronológico de actas">
      <p v-if="operationsStore.data.bitacora.length === 0" class="empty-state">
        No existen actas registradas en la bitácora.
      </p>
      <div v-else class="acta-list">
        <article v-for="acta in operationsStore.data.bitacora" :key="acta.id" class="acta-card">
          <header class="acta-card__header">
            <strong>Acta #{{ acta.id }} — {{ acta.fecha }} ({{ acta.hora }})</strong>
            <span class="acta-card__loc">{{ sanitizeUntrustedText(acta.ubicacion) }}</span>
          </header>
          <p class="acta-card__content">{{ sanitizeUntrustedText(acta.contenido) }}</p>
        </article>
      </div>
    </section>
  </AppShellLayout>
</template>

<style scoped>
.page-header {
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

.acta-form {
  padding: 1.25rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  margin-bottom: 1.25rem;
}

.inline-row {
  display: flex;
  gap: 0.75rem;
}

.field-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.875rem;
}

.field-label {
  font-size: 0.85rem;
  font-weight: 600;
}

.field-input {
  min-height: 44px;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
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

.acta-list {
  display: grid;
  gap: 0.875rem;
}

.acta-card {
  padding: 1rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
}

.acta-card__header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.35rem;
}

.acta-card__loc {
  font-size: 0.8rem;
  color: #475569;
}

.acta-card__content {
  margin: 0;
  font-size: 0.9rem;
  color: #334155;
}

.empty-state {
  padding: 1.25rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
}
</style>
