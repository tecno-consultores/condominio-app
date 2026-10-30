<script setup lang="ts">
import { onMounted, ref } from 'vue';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import { useOperationsStore } from '../../stores/operationsStore';
import { sanitizeUntrustedText } from '../../utils/security';

const operationsStore = useOperationsStore();

const area = ref('Cuarto de Bombas');
const comentario = ref('');
const urlFoto = ref('https://cdn.condominio.local/voceros/evidencia.avif');
const statusBanner = ref<string | null>(null);

onMounted(async () => {
  await operationsStore.fetchGaleriaVoceros();
});

async function handleSubmitPhoto(): Promise<void> {
  statusBanner.value = null;
  if (operationsStore.isPhotoQuotaExhausted) {
    operationsStore.errorMessage = 'Límite mensual de 30 fotografías alcanzado.';
    return;
  }
  try {
    await operationsStore.subirFotoVocero({
      periodo: operationsStore.data.galeriaVoceros.periodo,
      area: area.value,
      comentario: comentario.value.trim(),
      url_foto: urlFoto.value.trim(),
    });
    comentario.value = '';
    statusBanner.value = 'Fotografía registrada y encolada para optimización AVIF.';
  } catch {
    // Error almacenado en operationsStore.errorMessage
  }
}
</script>

<template>
  <AppShellLayout>
    <header class="page-header">
      <div>
        <h1 class="page-header__title">Galería de Inspección de Voceros</h1>
        <p class="page-header__subtitle">
          Registro fotográfico mensual de áreas comunes (máximo 30 fotos por mes calendario).
        </p>
      </div>
      <div id="photo-quota-badge" class="quota-box">
        <label for="photo-quota-progress" class="quota-box__label">
          Cuota mensual ({{ operationsStore.data.galeriaVoceros.periodo }}):
          <strong>
            {{ operationsStore.data.galeriaVoceros.fotos_usadas_mes }} /
            {{ operationsStore.data.galeriaVoceros.limite_mensual }} fotos
          </strong>
        </label>
        <progress
          id="photo-quota-progress"
          class="quota-box__bar"
          :max="operationsStore.data.galeriaVoceros.limite_mensual"
          :value="operationsStore.data.galeriaVoceros.fotos_usadas_mes"
        />
      </div>
    </header>

    <div v-if="operationsStore.errorMessage" class="banner banner--error" role="alert">
      {{ operationsStore.errorMessage }}
    </div>
    <div v-if="statusBanner" class="banner banner--success" role="status">
      {{ statusBanner }}
    </div>

    <form class="upload-form" @submit.prevent="handleSubmitPhoto">
      <div class="field-group">
        <label for="input-vocero-area" class="field-label">Área inspeccionada</label>
        <input id="input-vocero-area" v-model="area" type="text" required class="field-input" />
      </div>

      <div class="field-group">
        <label for="input-vocero-comentario" class="field-label">Observación técnica</label>
        <input
          id="input-vocero-comentario"
          v-model="comentario"
          type="text"
          required
          class="field-input"
        />
      </div>

      <div class="field-group">
        <label for="input-vocero-url" class="field-label">URL de evidencia (AVIF / S3 MinIO)</label>
        <input id="input-vocero-url" v-model="urlFoto" type="url" required class="field-input" />
      </div>

      <button
        id="btn-submit-vocero-foto"
        type="submit"
        class="btn-primary"
        :disabled="operationsStore.isPhotoQuotaExhausted || operationsStore.isLoading"
      >
        {{
          operationsStore.isPhotoQuotaExhausted
            ? 'Cuota de 30 Fotos Agotada'
            : 'Subir Fotografía de Inspección'
        }}
      </button>
    </form>

    <section aria-label="Fotografías publicadas en el mes">
      <p v-if="operationsStore.data.galeriaVoceros.fotos.length === 0" class="empty-state">
        Aún no se han cargado fotografías de inspección en este periodo.
      </p>
      <div v-else class="gallery-grid">
        <article
          v-for="foto in operationsStore.data.galeriaVoceros.fotos"
          :key="foto.id"
          class="gallery-card"
        >
          <header class="gallery-card__header">
            <strong>{{ sanitizeUntrustedText(foto.area) }}</strong>
            <span class="avif-pill">AVIF</span>
          </header>
          <p class="gallery-card__comment">{{ sanitizeUntrustedText(foto.comentario) }}</p>
        </article>
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

.quota-box {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 220px;
}

.quota-box__label {
  font-size: 0.825rem;
  color: #0f172a;
}

.quota-box__bar {
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

.upload-form {
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

.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.gallery-grid {
  display: grid;
  gap: 0.875rem;
}

.gallery-card {
  padding: 1rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
}

.gallery-card__header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.35rem;
}

.avif-pill {
  padding: 0.15rem 0.45rem;
  border-radius: 9999px;
  background-color: #e0f2fe;
  color: #0369a1;
  font-size: 0.725rem;
  font-weight: 700;
}

.gallery-card__comment {
  margin: 0;
  font-size: 0.875rem;
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
