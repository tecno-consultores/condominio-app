<script setup lang="ts">
import { ref } from 'vue';
import { useAccessAmenitiesStore } from '../../stores/accessAmenitiesStore';

const store = useAccessAmenitiesStore();
const qrTokenInput = ref('');

async function handleVerificarQR(): Promise<void> {
  if (!qrTokenInput.value.trim()) {
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

    <form
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
        <span class="result-card__jti">JTI: {{ store.ultimoEscaneo.jti }}</span>
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
  color: #0f172a;
  margin: 0;
}

.scanner-view__subtitle {
  color: #475569;
  font-size: 0.92rem;
  margin: 0.25rem 0 0;
}

.card {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 0.75rem;
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
  color: #1e293b;
}

.field input {
  padding: 0.65rem 0.8rem;
  border: 1px solid #94a3b8;
  border-radius: 0.5rem;
  font-size: 0.95rem;
  color: #0f172a;
}

.btn {
  padding: 0.65rem 1.1rem;
  border-radius: 0.5rem;
  font-weight: 700;
  cursor: pointer;
  border: none;
}

.btn--primary {
  background: #0369a1;
  color: #ffffff;
}

.alert--error {
  padding: 0.9rem 1rem;
  border-radius: 0.6rem;
  background: #fef2f2;
  border: 1px solid #ef4444;
  color: #991b1b;
}

.result-card {
  border-left: 4px solid #16a34a;
}

.result-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.badge--authorized {
  background: #dcfce7;
  color: #14532d;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.2rem 0.6rem;
  border-radius: 9999px;
}

.result-card__jti {
  font-size: 0.75rem;
  color: #475569;
  font-family: monospace;
}

.result-card__visitor {
  margin: 0 0 0.35rem;
  font-size: 1.15rem;
  color: #0f172a;
}

.result-card__detail {
  margin: 0.2rem 0;
  color: #1e293b;
  font-size: 0.9rem;
}

.result-card__message {
  margin: 0.5rem 0 0;
  font-weight: 600;
  color: #14532d;
}
</style>
