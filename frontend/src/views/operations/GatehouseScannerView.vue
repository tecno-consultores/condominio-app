<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useAccessAmenitiesStore } from '../../stores/accessAmenitiesStore';
import { useAuthStore } from '../../stores/authStore';

const authStore = useAuthStore();
const store = useAccessAmenitiesStore();
const qrTokenInput = ref('');

const canVerifyQr = computed(() => {
  const rol = authStore.userRole;
  return rol === 'CONSERJE' || rol === 'PRESIDENTE' || rol === 'VOCERO';
});

async function handleVerificarQR(): Promise<void> {
  if (!canVerifyQr.value || !qrTokenInput.value.trim()) {
    return;
  }
  try {
    await store.verificarPaseQR(qrTokenInput.value.trim());
  } catch {
    // El error de firma o Anti-Replay se expone en store.error
  }
}
</script>

<template>
  <section class="scanner-view" aria-labelledby="scanner-title">
    <header class="scanner-view__header">
      <h1 id="scanner-title" class="scanner-view__title">
        Escáner y Verificador de Pases QR en Garita
      </h1>
      <p class="scanner-view__subtitle">
        Valide en tiempo constante la firma HMAC-SHA256 y la unicidad Anti-Replay del visitante.
      </p>
    </header>

    <div v-if="!canVerifyQr" id="scanner-rbac-warning" class="alert alert--error" role="alert">
      Acceso exclusivo para Conserjería o Junta Directiva.
    </div>

    <form
      v-else
      id="form-verificar-qr-garita"
      class="card scanner-form"
      aria-label="Formulario de verificación de pase QR en garita"
      @submit.prevent="handleVerificarQR"
    >
      <label class="field" for="input-scan-qr-token">
        <span>Token Criptográfico del Pase QR</span>
        <input
          id="input-scan-qr-token"
          v-model="qrTokenInput"
          type="text"
          placeholder="Pegue o escanee el código base64url.firma_hmac…"
          required
        />
      </label>

      <button id="btn-verify-qr" type="submit" class="btn btn--primary" :disabled="store.isLoading">
        {{ store.isLoading ? 'Verificando Firma y Nonce…' : 'Verificar Pase QR en Garita' }}
      </button>
    </form>

    <div v-if="store.error" id="qr-scan-error-alert" class="alert alert--error" role="alert">
      <strong>Acceso Denegado:</strong> {{ store.error }}
    </div>

    <article
      v-if="store.ultimoEscaneo && !store.error"
      id="qr-scan-success-card"
      class="card result-card"
      aria-live="polite"
    >
      <div class="result-card__header">
        <span class="badge badge--authorized">ACCESO AUTORIZADO</span>
        <span class="result-card__modality">
          {{ store.ultimoEscaneo.estado }} · {{ store.ultimoEscaneo.modalidad }}
        </span>
      </div>

      <h2 class="result-card__visitor">{{ store.ultimoEscaneo.nombre_visitante }}</h2>
      <p class="result-card__detail">
        <strong>Cédula:</strong> {{ store.ultimoEscaneo.cedula_visitante }} ·
        <strong>Unidad Destino:</strong> {{ store.ultimoEscaneo.identificador_unidad }}
      </p>
      <p v-if="store.ultimoEscaneo.placa_vehiculo" class="result-card__detail">
        <strong>Vehículo Autorizado:</strong> {{ store.ultimoEscaneo.placa_vehiculo }}
      </p>
      <p class="result-card__message">{{ store.ultimoEscaneo.mensaje }}</p>
    </article>
  </section>
</template>

<style scoped>
.scanner-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.scanner-view__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.scanner-view__subtitle {
  color: var(--text-secondary);
  font-size: 0.92rem;
  margin: 0.25rem 0 0;
}

.card {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 1.25rem;
}

.scanner-form {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-primary);
}

.field input {
  min-block-size: 2.75rem;
  padding: 0.65rem 0.8rem;
  border: 1px solid var(--border-control);
  background: var(--surface-card);
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
  color: var(--text-primary);
}

.btn {
  min-block-size: 2.75rem;
  padding: 0.65rem 1.1rem;
  border-radius: var(--radius-sm);
  font-weight: 700;
  cursor: pointer;
  border: none;
}

.btn--primary {
  background: var(--brand-600);
  color: var(--text-on-accent);
}

.alert--error {
  padding: 0.9rem 1rem;
  border-radius: var(--radius-sm);
  background: var(--status-danger-bg);
  border: 1px solid var(--status-danger-border);
  color: var(--status-danger-text);
}

.result-card {
  border-left: 4px solid var(--status-ok-border);
}

.result-card__header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.badge--authorized {
  background: var(--status-ok-bg);
  color: var(--status-ok-text);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-pill);
}

.result-card__modality {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.result-card__visitor {
  margin: 0 0 0.35rem;
  font-size: 1.15rem;
  color: var(--text-primary);
}

.result-card__detail {
  margin: 0.2rem 0;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.result-card__message {
  margin: 0.5rem 0 0;
  font-weight: 600;
  color: var(--status-ok-text);
}
</style>
