<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useAccessAmenitiesStore, type ModalidadPaseQR } from '../../stores/accessAmenitiesStore';

const store = useAccessAmenitiesStore();

const unidadId = ref<number>(1);
const nombreVisitante = ref('');
const cedulaVisitante = ref('');
const placaVehiculo = ref('');
const modalidad = ref<ModalidadPaseQR>('UNICO_USO');
const horasValidez = ref<number>(24);
const feedbackExito = ref<string | null>(null);
const tokenCopiadoId = ref<number | null>(null);

onMounted(async () => {
  await store.fetchMisPases();
});

async function handleCrearPase(): Promise<void> {
  feedbackExito.value = null;
  if (!nombreVisitante.value.trim() || !cedulaVisitante.value.trim()) {
    return;
  }
  try {
    const creado = await store.crearPaseVisita({
      unidad_id: Number(unidadId.value),
      nombre_visitante: nombreVisitante.value.trim(),
      cedula_visitante: cedulaVisitante.value.trim(),
      placa_vehiculo: placaVehiculo.value.trim() || null,
      modalidad: modalidad.value,
      horas_validez: Number(horasValidez.value),
    });
    feedbackExito.value = `Pase QR emitido para ${creado.nombre_visitante} (JTI: ${creado.jti.slice(0, 8)}…).`;
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
    feedbackExito.value = `Pase #${paseId} revocado e invalidado en garita.`;
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
    </header>

    <div v-if="store.error" id="passes-error-banner" class="alert alert--error" role="alert">
      {{ store.error }}
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
          <span>ID de Unidad Anfitriona</span>
          <input id="input-pase-unidad" v-model.number="unidadId" type="number" min="1" required />
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
            v-model.number="horasValidez"
            type="number"
            min="1"
            max="72"
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

.passes-view__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-primary, #0f172a);
  margin: 0;
}

.passes-view__subtitle {
  color: var(--text-secondary, #475569);
  font-size: 0.92rem;
  margin: 0.25rem 0 0;
}

.card {
  background: var(--surface-card, #ffffff);
  border: 1px solid var(--border-subtle, #cbd5e1);
  border-radius: var(--radius-md, 0.75rem);
  padding: 1.25rem;
  box-shadow: var(--shadow-card);
}

.card__title,
.section-heading {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary, #0f172a);
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
  color: var(--text-primary, #1e293b);
}

.field input,
.field select {
  padding: 0.6rem 0.75rem;
  border: 1px solid var(--border-control, #94a3b8);
  border-radius: var(--radius-sm, 0.5rem);
  font-size: 0.92rem;
  color: var(--text-primary, #0f172a);
  background: var(--surface-card, #ffffff);
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
  color: var(--text-primary, #0f172a);
}

.pass-card__meta {
  margin: 0.2rem 0 0;
  font-size: 0.83rem;
  color: var(--text-secondary, #475569);
}

.pass-card__token-box {
  background: var(--surface-subtle, #f8fafc);
  border: 1px dashed var(--border-control, #94a3b8);
  border-radius: var(--radius-sm, 0.5rem);
  padding: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.token-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary, #475569);
}

.token-value {
  font-size: 0.78rem;
  color: var(--text-primary, #0f172a);
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
  border-radius: var(--radius-pill, 9999px);
}

.badge--activo {
  background: var(--status-ok-bg, #dcfce7);
  color: var(--status-ok-text, #14532d);
}

.badge--usado {
  background: var(--brand-tint, #e0f2fe);
  color: var(--brand-accent, #0c4a6e);
}

.badge--revocado,
.badge--expirado {
  background: var(--status-danger-bg, #fee2e2);
  color: var(--status-danger-text, #7f1d1d);
}

.btn {
  padding: 0.6rem 1rem;
  border-radius: var(--radius-sm, 0.5rem);
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.btn--primary {
  background: var(--brand-600, #0369a1);
  color: #ffffff;
}

.btn--secondary {
  background: var(--surface-subtle, #e2e8f0);
  border: 1px solid var(--border-control, #cbd5e1);
  color: var(--text-primary, #0f172a);
}

.btn--danger {
  background: #b91c1c;
  color: #ffffff;
}

.alert {
  padding: 0.8rem 1rem;
  border-radius: var(--radius-sm, 0.5rem);
  font-weight: 600;
}

.alert--error {
  background: var(--status-danger-bg, #fef2f2);
  border: 1px solid var(--status-danger-border, #ef4444);
  color: var(--status-danger-text, #991b1b);
}

.alert--success {
  background: var(--status-ok-bg, #f0fdf4);
  border: 1px solid var(--status-ok-border, #22c55e);
  color: var(--status-ok-text, #14532d);
}

.empty-state {
  color: var(--text-secondary, #475569);
  font-size: 0.9rem;
}
</style>
