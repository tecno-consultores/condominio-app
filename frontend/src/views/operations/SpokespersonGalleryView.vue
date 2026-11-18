<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useDualRefresh } from '../../composables/useDualRefresh';
import { useAuthStore } from '../../stores/authStore';
import { useFinanceStore } from '../../stores/financeStore';
import { useOperationsStore } from '../../stores/operationsStore';
import { isSafeMediaUrl, validateProofFileUpload } from '../../utils/security';

const authStore = useAuthStore();
const financeStore = useFinanceStore();
const operationsStore = useOperationsStore();

const area = ref('Cuarto de Bombas');
const comentario = ref('');
const urlFoto = ref('');
const selectedFile = ref<File | null>(null);
const selectedFileName = ref<string | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);
const statusBanner = ref<string | null>(null);

const canUploadGallery = computed(() => {
  const rol = authStore.userRole;
  return rol === 'VOCERO' || rol === 'PRESIDENTE';
});

const { isRefreshing, triggerRefresh } = useDualRefresh(() =>
  operationsStore.fetchGaleriaVoceros(),
);

onMounted(async () => {
  await operationsStore.fetchGaleriaVoceros();
});

function handleFileChange(event: Event): void {
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
    operationsStore.errorMessage = check.error ?? 'Archivo fotográfico inválido.';
    selectedFile.value = null;
    selectedFileName.value = null;
    input.value = '';
    return;
  }
  selectedFile.value = file;
  selectedFileName.value = file.name;
}

function isProcessingUrl(url: string | null | undefined): boolean {
  return Boolean(url && url.trim().startsWith('s3://'));
}

async function handleSubmitPhoto(): Promise<void> {
  statusBanner.value = null;
  if (operationsStore.isPhotoQuotaExhausted) {
    operationsStore.errorMessage = 'Límite mensual de 30 fotografías alcanzado.';
    return;
  }

  let resolvedUrl = urlFoto.value.trim();
  if (!selectedFile.value && !resolvedUrl) {
    operationsStore.errorMessage = 'Selecciona un archivo de imagen o indica una URL válida.';
    return;
  }

  try {
    if (selectedFile.value) {
      const upload = await financeStore.subirEvidencia(selectedFile.value, 'voceros');
      resolvedUrl = upload.url;
    }
    await operationsStore.subirFotoVocero({
      periodo: operationsStore.data.galeriaVoceros.periodo,
      area: area.value.trim(),
      comentario: comentario.value.trim(),
      url_foto: resolvedUrl,
    });
    comentario.value = '';
    urlFoto.value = '';
    selectedFile.value = null;
    selectedFileName.value = null;
    if (fileInputRef.value) {
      fileInputRef.value.value = '';
    }
    statusBanner.value = 'Fotografía registrada y encolada para optimización AVIF.';
  } catch {
    // Error almacenado en operationsStore.errorMessage / financeStore.errorMessage
  }
}
</script>

<template>
  <section aria-labelledby="spokesperson-gallery-title">
    <header class="page-header">
      <div>
        <h1 id="spokesperson-gallery-title" class="page-header__title">
          Galería de Inspección de Voceros
        </h1>
        <p class="page-header__subtitle">
          Registro fotográfico mensual de áreas comunes (máximo 30 fotos por mes calendario).
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

    <form v-if="canUploadGallery" class="upload-form" @submit.prevent="handleSubmitPhoto">
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
        <label for="input-vocero-archivo" class="field-label">
          Fotografía de inspección (JPG, PNG, WEBP, AVIF — máx. 2 MB)
        </label>
        <input
          id="input-vocero-archivo"
          ref="fileInputRef"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/avif"
          class="field-input"
          @change="handleFileChange"
        />
        <p v-if="selectedFileName" class="field-hint">Archivo validado: {{ selectedFileName }}</p>
      </div>

      <div class="field-group">
        <label for="input-vocero-url" class="field-label">
          URL directa alternativa (opcional si adjuntas archivo)
        </label>
        <input id="input-vocero-url" v-model="urlFoto" type="url" class="field-input" />
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
            <strong>{{ foto.area }}</strong>
            <span class="avif-pill">AVIF</span>
          </header>
          <img
            v-if="isSafeMediaUrl(foto.url_foto)"
            :src="foto.url_foto.trim()"
            :alt="`Inspección en ${foto.area}: ${foto.comentario}`"
            loading="lazy"
            decoding="async"
            class="gallery-card__image"
          />
          <p v-else-if="isProcessingUrl(foto.url_foto)" class="gallery-card__processing">
            Evidencia en procesamiento multimedia AVIF
          </p>
          <p class="gallery-card__comment">{{ foto.comentario }}</p>
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

.quota-box {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 220px;
}

.quota-box__label {
  font-size: 0.825rem;
  color: var(--text-primary);
}

.quota-box__bar {
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

.upload-form {
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
  margin-bottom: 0.875rem;
}

.field-label {
  font-size: 0.85rem;
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

.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr));
  gap: 0.875rem;
}

.gallery-card {
  padding: 1rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.gallery-card__header {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}

.gallery-card__image {
  inline-size: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
}

.gallery-card__processing {
  margin: 0;
  padding: 0.5rem;
  border-radius: var(--radius-sm);
  background-color: var(--status-info-bg);
  color: var(--status-info-text);
  font-size: 0.8rem;
  font-weight: 600;
}

.avif-pill {
  padding: 0.15rem 0.45rem;
  border-radius: var(--radius-pill);
  background-color: var(--status-info-bg);
  color: var(--status-info-text);
  font-size: 0.725rem;
  font-weight: 700;
}

.gallery-card__comment {
  margin: 0;
  font-size: 0.875rem;
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
