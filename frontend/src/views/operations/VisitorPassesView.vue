<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useDualRefresh } from '../../composables/useDualRefresh';
import { useAccessAmenitiesStore, type ModalidadPaseQR } from '../../stores/accessAmenitiesStore';
import { useAuthStore } from '../../stores/authStore';
import { useOperationsStore } from '../../stores/operationsStore';

const authStore = useAuthStore();
const opsStore = useOperationsStore();
const store = useAccessAmenitiesStore();

const unidadId = ref<number>(1);
const nombreVisitante = ref('');
const cedulaVisitante = ref('');
const placaVehiculo = ref('');
const modalidad = ref<ModalidadPaseQR>('UNICO_USO');
const horasValidez = ref('24');
const feedbackExito = ref<string | null>(null);
const validationError = ref<string | null>(null);
const tokenCopiadoId = ref<number | null>(null);

async function refreshPassesData(): Promise<void> {
  await Promise.allSettled([store.fetchMisPases(), opsStore.fetchUnidades()]);
  if (authStore.activeUnitId !== null) {
    unidadId.value = authStore.activeUnitId;
  } else if (
    opsStore.data.unidades.length > 0 &&
    !opsStore.data.unidades.some((u) => u.id === unidadId.value)
  ) {
    unidadId.value = opsStore.data.unidades[0].id;
  }
}

const { isRefreshing, triggerRefresh } = useDualRefresh(refreshPassesData);

onMounted(async () => {
  await refreshPassesData();
});

async function handleCrearPase(): Promise<void> {
  feedbackExito.value = null;
  validationError.value = null;
  if (!nombreVisitante.value.trim() || !cedulaVisitante.value.trim()) {
    return;
  }
  const rawHoras = String(horasValidez.value ?? '').trim();
  const parsedHoras = Number.parseInt(rawHoras, 10);
  if (!/^\d+$/.test(rawHoras) || parsedHoras < 1 || parsedHoras > 72) {
    validationError.value = 'La vigencia debe ser un número entero entre 1 y 72 horas.';
    return;
  }
  try {
    const creado = await store.crearPaseVisita({
      unidad_id: Number(unidadId.value),
      nombre_visitante: nombreVisitante.value.trim(),
      cedula_visitante: cedulaVisitante.value.trim(),
      placa_vehiculo: placaVehiculo.value.trim() || null,
      modalidad: modalidad.value,
      horas_validez: parsedHoras,
    });
    feedbackExito.value = `Pase QR emitido para ${creado.nombre_visitante}.`;
    nombreVisitante.value = '';
    cedulaVisitante.value = '';
    placaVehiculo.value = '';
  } catch {
    // Error gestionado reactivamente en el store
  }
}

async function handleCopiarToken(paseId: number, qrToken: string): Promise<void> {
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(qrToken);
    } catch {
      // Fallback silencioso en entornos restringidos
    }
  }
  tokenCopiadoId.value = paseId;
}

async function handleRevocarPase(paseId: number): Promise<void> {
  feedbackExito.value = null;
  try {
    await store.revocarPaseVisita(paseId);
    feedbackExito.value = 'Pase de visita revocado e invalidado en garita.';
  } catch {
    // Error gestionado reactivamente en el store
  }
}
</script>

<template>
  <section class="passes-view" aria-labelledby="passes-title">
    <header class="passes-view__header">
      <div>
        <h1 id="passes-title" class="passes-view__title">
          Pases de Visita QR Firmados (HMAC-SHA256)
        </h1>
        <p class="passes-view__subtitle">
          Emita autorizaciones peatonales o vehiculares con protección Anti-Replay en garita.
        </p>
      </div>
      <button
        id="btn-dual-refresh"
        type="button"
        class="dual-refresh-btn"
        :disabled="isRefreshing || store.isLoading"
        @click="triggerRefresh"
      >
        <span aria-hidden="true">🔄</span>
        <span>{{ isRefreshing ? 'Actualizando...' : 'Refrescar' }}</span>
      </button>
    </header>

    <div v-if="store.error" id="passes-error-banner" class="alert alert--error" role="alert">
      {{ store.error }}
    </div>
    <div v-if="validationError" class="alert alert--error" role="alert">
      {{ validationError }}
    </div>
    <div v-if="feedbackExito" id="passes-success-banner" class="alert alert--success" role="status">
      {{ feedbackExito }}
    </div>

    <form
      id="form-crear-pase-qr"
      class="card form-grid"
      aria-label="Emitir nuevo pase de visita QR"
      @submit.prevent="handleCrearPase"
    >
      <h2 class="card__title">Nueva Autorización de Ingreso</h2>

      <div class="field-row">
        <label class="field" for="input-pase-unidad">
          <span>Unidad Anfitriona</span>
          <select id="input-pase-unidad" v-model.number="unidadId" required>
            <option v-for="u in opsStore.data.unidades" :key="u.id" :value="u.id">
              {{ u.identificador }}
            </option>
          </select>
        </label>

        <label class="field" for="select-pase-modalidad">
          <span>Modalidad del Pase</span>
          <select id="select-pase-modalidad" v-model="modalidad">
            <option value="UNICO_USO">Único Uso (Se quema al escanear)</option>
            <option value="VENTANA_TEMPORAL">Ventana Temporal (Múltiples ingresos)</option>
          </select>
        </label>

        <label class="field" for="input-pase-horas">
          <span>Vigencia (Horas, máx. 72h)</span>
          <input
            id="input-pase-horas"
            v-model="horasValidez"
            type="number"
            min="1"
            max="72"
            step="1"
            required
          />
        </label>
      </div>

      <div class="field-row">
        <label class="field" for="input-pase-nombre">
          <span>Nombre Completo del Visitante o Técnico</span>
          <input
            id="input-pase-nombre"
            v-model="nombreVisitante"
            type="text"
            minlength="3"
            maxlength="120"
            placeholder="Ej. Carlos Mendoza (Técnico Fibra)"
            required
          />
        </label>

        <label class="field" for="input-pase-cedula">
          <span>Cédula / Documento</span>
          <input
            id="input-pase-cedula"
            v-model="cedulaVisitante"
            type="text"
            minlength="5"
            maxlength="25"
            placeholder="Ej. V-19888777"
            required
          />
        </label>

        <label class="field" for="input-pase-placa">
          <span>Placa Vehicular (Opcional)</span>
          <input
            id="input-pase-placa"
            v-model="placaVehiculo"
            type="text"
            maxlength="20"
            placeholder="Ej. AB123CD"
          />
        </label>
      </div>

      <button
        id="btn-submit-pase-qr"
        type="submit"
        class="btn btn--primary"
        :disabled="store.isLoading"
      >
        {{ store.isLoading ? 'Firmando Pase QR…' : 'Emitir Pase QR Firmado' }}
      </button>
    </form>

    <section class="passes-list" aria-label="Mis pases de visita emitidos">
      <h2 class="section-heading">Mis Pases Emitidos ({{ store.pases.length }})</h2>

      <p v-if="store.pases.length === 0" id="passes-empty-state" class="empty-state">
        Aún no ha emitido pases de visita QR para su unidad.
      </p>

      <div class="cards-grid defer-feed-list">
        <article
          v-for="pase in store.pases"
          :id="`qr-pass-card-${pase.id}`"
          :key="pase.id"
          class="card pass-card"
        >
          <div class="pass-card__top">
            <div>
              <strong class="pass-card__visitor">{{ pase.nombre_visitante }}</strong>
              <p class="pass-card__meta">
                C.I.: {{ pase.cedula_visitante }} · Unidad {{ pase.identificador_unidad }}
                <span v-if="pase.placa_vehiculo"> · Placa: {{ pase.placa_vehiculo }}</span>
              </p>
            </div>
            <span class="badge" :class="`badge--${pase.estado.toLowerCase()}`">
              {{ pase.estado }}
            </span>
          </div>

          <div class="pass-card__token-box">
            <span class="token-label">Token QR Criptográfico ({{ pase.modalidad }}):</span>
            <code :id="`qr-token-code-${pase.id}`" class="token-value">{{ pase.qr_token }}</code>
          </div>

          <div class="pass-card__actions">
            <button
              :id="`btn-copy-qr-${pase.id}`"
              type="button"
              class="btn btn--secondary"
              @click="handleCopiarToken(pase.id, pase.qr_token)"
            >
              {{ tokenCopiadoId === pase.id ? 'Token Copiado' : 'Copiar Token QR' }}
            </button>

            <button
              v-if="pase.estado === 'ACTIVO'"
              :id="`btn-revoke-qr-${pase.id}`"
              type="button"
              class="btn btn--danger"
              @click="handleRevocarPase(pase.id)"
            >
              Revocar Pase
            </button>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>

<style scoped>
.passes-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.passes-view__header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.passes-view__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.passes-view__subtitle {
  color: var(--text-secondary);
  font-size: 0.92rem;
  margin: 0.25rem 0 0;
}

.card {
  background: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 1.25rem;
  box-shadow: var(--shadow-card);
}

.card__title,
.section-heading {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 0.75rem;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 0.85rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-primary);
}

.field input,
.field select {
  min-block-size: 2.75rem;
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--border-control);
  border-radius: var(--radius-sm);
  font-size: 0.92rem;
  color: var(--text-primary);
  background: var(--surface-card);
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
  gap: 1rem;
}

.pass-card {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.pass-card__top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
}

.pass-card__visitor {
  font-size: 1rem;
  color: var(--text-primary);
}

.pass-card__meta {
  margin: 0.2rem 0 0;
  font-size: 0.83rem;
  color: var(--text-secondary);
}

.pass-card__token-box {
  background: var(--surface-subtle);
  border: 1px dashed var(--border-control);
  border-radius: var(--radius-sm);
  padding: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.token-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.token-value {
  font-size: 0.78rem;
  color: var(--text-primary);
  word-break: break-all;
}

.pass-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.badge {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-pill);
}

.badge--activo {
  background: var(--status-ok-bg);
  color: var(--status-ok-text);
}

.badge--usado {
  background: var(--brand-tint);
  color: var(--brand-accent);
}

.badge--revocado,
.badge--expirado {
  background: var(--status-danger-bg);
  color: var(--status-danger-text);
}

.btn {
  min-block-size: 2.75rem;
  padding: 0.6rem 1rem;
  border-radius: var(--radius-sm);
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn--primary {
  background: var(--brand-600);
  color: var(--text-on-accent);
}

.btn--secondary {
  background: var(--surface-subtle);
  border-color: var(--border-control);
  color: var(--text-primary);
}

.btn--danger {
  background: var(--status-danger-bg);
  border-color: var(--status-danger-border);
  color: var(--status-danger-text);
}

.alert {
  padding: 0.8rem 1rem;
  border-radius: var(--radius-sm);
  font-weight: 600;
}

.alert--error {
  background: var(--status-danger-bg);
  border: 1px solid var(--status-danger-border);
  color: var(--status-danger-text);
}

.alert--success {
  background: var(--status-ok-bg);
  border: 1px solid var(--status-ok-border);
  color: var(--status-ok-text);
}

.empty-state {
  color: var(--text-secondary);
  font-size: 0.9rem;
}
</style>
