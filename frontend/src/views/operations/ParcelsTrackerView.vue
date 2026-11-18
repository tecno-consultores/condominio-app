<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useDualRefresh } from '../../composables/useDualRefresh';
import { useAccessAmenitiesStore, type PaqueteDTO } from '../../stores/accessAmenitiesStore';
import { useAuthStore } from '../../stores/authStore';
import { useOperationsStore } from '../../stores/operationsStore';
import { isSafeMediaUrl } from '../../utils/security';

const authStore = useAuthStore();
const opsStore = useOperationsStore();
const store = useAccessAmenitiesStore();

const unidadId = ref<number>(1);
const empresaEnvio = ref('ZOOM');
const descripcion = ref('');
const urlFotoEvidencia = ref('');
const feedbackExito = ref<string | null>(null);

const canManageParcels = computed(() => {
  const rol = authStore.userRole;
  return rol === 'CONSERJE' || rol === 'PRESIDENTE';
});

function canConfirmDelivery(paquete: PaqueteDTO): boolean {
  if (canManageParcels.value) {
    return true;
  }
  return authStore.activeUnitId !== null && authStore.activeUnitId === paquete.unidad_id;
}

function isProcessingUrl(url: string | null | undefined): boolean {
  return Boolean(url && url.trim().startsWith('s3://'));
}

async function refreshParcelsData(): Promise<void> {
  await Promise.allSettled([store.fetchPaqueteria(), opsStore.fetchUnidades()]);
  if (
    opsStore.data.unidades.length > 0 &&
    !opsStore.data.unidades.some((u) => u.id === unidadId.value)
  ) {
    unidadId.value = opsStore.data.unidades[0].id;
  }
}

const { isRefreshing, triggerRefresh } = useDualRefresh(refreshParcelsData);

onMounted(async () => {
  await refreshParcelsData();
});

async function handleRegistrarPaquete(): Promise<void> {
  feedbackExito.value = null;
  if (!canManageParcels.value || !descripcion.value.trim()) {
    return;
  }
  try {
    const creado = await store.registrarPaquete({
      unidad_id: Number(unidadId.value),
      empresa_envio: empresaEnvio.value.trim(),
      descripcion: descripcion.value.trim(),
      url_foto_evidencia: urlFotoEvidencia.value.trim() || null,
    });
    feedbackExito.value = `Encomienda registrada para Unidad ${creado.identificador_unidad}.`;
    descripcion.value = '';
    urlFotoEvidencia.value = '';
  } catch {
    // Error expuesto reactivamente en store.error
  }
}

async function handleConfirmarEntrega(paqueteId: number): Promise<void> {
  feedbackExito.value = null;
  try {
    await store.confirmarEntregaPaquete(paqueteId);
    feedbackExito.value = 'Paquete marcado como ENTREGADO.';
  } catch {
    // Error expuesto reactivamente en store.error
  }
}
</script>

<template>
  <section class="parcels-view" aria-labelledby="parcels-title">
    <header class="parcels-view__header">
      <div>
        <h1 id="parcels-title" class="parcels-view__title">
          Control de Paquetería y Encomiendas en Garita
        </h1>
        <p class="parcels-view__subtitle">
          Cadena de custodia desde la recepción en conserjería hasta el retiro confirmado por la
          unidad.
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

    <div v-if="store.error" id="parcels-error-banner" class="alert alert--error" role="alert">
      {{ store.error }}
    </div>
    <div
      v-if="feedbackExito"
      id="parcels-success-banner"
      class="alert alert--success"
      role="status"
    >
      {{ feedbackExito }}
    </div>

    <form
      v-if="canManageParcels"
      id="form-registrar-paquete"
      class="card form-grid"
      aria-label="Registrar recepción de paquete en garita"
      @submit.prevent="handleRegistrarPaquete"
    >
      <h2 class="card__title">Recepción de Encomienda en Conserjería</h2>

      <div class="field-row">
        <label class="field" for="input-parcel-unidad">
          <span>Unidad Destinataria</span>
          <select id="input-parcel-unidad" v-model.number="unidadId" required>
            <option v-for="u in opsStore.data.unidades" :key="u.id" :value="u.id">
              {{ u.identificador }}
            </option>
          </select>
        </label>

        <label class="field" for="select-parcel-empresa">
          <span>Empresa de Envío / Courier</span>
          <select id="select-parcel-empresa" v-model="empresaEnvio">
            <option value="ZOOM">ZOOM</option>
            <option value="MRW">MRW</option>
            <option value="TEALCA">TEALCA</option>
            <option value="MERCADOLIBRE">MERCADOLIBRE</option>
            <option value="PEDIDOSYA">PEDIDOSYA</option>
            <option value="OTRO">OTRO</option>
          </select>
        </label>
      </div>

      <div class="field-row">
        <label class="field" for="input-parcel-descripcion">
          <span>Descripción del Paquete o Sobre</span>
          <input
            id="input-parcel-descripcion"
            v-model="descripcion"
            type="text"
            minlength="3"
            maxlength="200"
            placeholder="Ej. Caja sellada mediana con guía"
            required
          />
        </label>

        <label class="field" for="input-parcel-foto">
          <span>URI de Evidencia Fotográfica (Opcional)</span>
          <input
            id="input-parcel-foto"
            v-model="urlFotoEvidencia"
            type="text"
            placeholder="https://.../paquete.avif"
          />
        </label>
      </div>

      <button
        id="btn-submit-parcel"
        type="submit"
        class="btn btn--primary"
        :disabled="store.isLoading"
      >
        {{ store.isLoading ? 'Registrando Encomienda…' : 'Registrar Paquete en Garita' }}
      </button>
    </form>

    <section class="parcels-list" aria-label="Listado de paquetes en garita e historial">
      <h2 class="section-heading">Bandeja de Paquetería ({{ store.paquetes.length }})</h2>

      <p v-if="store.paquetes.length === 0" id="parcels-empty-state" class="empty-state">
        No hay paquetes pendientes ni registrados actualmente.
      </p>

      <div class="cards-grid defer-feed-list">
        <article
          v-for="paquete in store.paquetes"
          :id="`parcel-card-${paquete.id}`"
          :key="paquete.id"
          class="card parcel-card"
        >
          <div class="parcel-card__top">
            <div>
              <strong class="parcel-card__courier">
                {{ paquete.empresa_envio }} · Unidad {{ paquete.identificador_unidad }}
              </strong>
              <p class="parcel-card__desc">{{ paquete.descripcion }}</p>
            </div>
            <span class="badge" :class="`badge--${paquete.estado.toLowerCase()}`">
              {{ paquete.estado }}
            </span>
          </div>

          <img
            v-if="isSafeMediaUrl(paquete.url_foto_evidencia)"
            :src="paquete.url_foto_evidencia!.trim()"
            :alt="`Evidencia de encomienda ${paquete.empresa_envio}`"
            loading="lazy"
            decoding="async"
            class="parcel-card__image"
          />
          <p
            v-else-if="isProcessingUrl(paquete.url_foto_evidencia)"
            class="parcel-card__processing"
          >
            Evidencia fotográfica en procesamiento multimedia
          </p>

          <div
            v-if="paquete.estado === 'EN_GARITA' && canConfirmDelivery(paquete)"
            class="parcel-card__actions"
          >
            <button
              :id="`btn-confirm-parcel-${paquete.id}`"
              type="button"
              class="btn btn--primary"
              @click="handleConfirmarEntrega(paquete.id)"
            >
              Confirmar Retiro / Entrega
            </button>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>

<style scoped>
.parcels-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.parcels-view__header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.parcels-view__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.parcels-view__subtitle {
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
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
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

.parcel-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.parcel-card__top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
}

.parcel-card__courier {
  font-size: 0.98rem;
  color: var(--text-primary);
}

.parcel-card__desc {
  margin: 0.25rem 0 0;
  font-size: 0.86rem;
  color: var(--text-secondary);
}

.parcel-card__image {
  inline-size: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
}

.parcel-card__processing {
  margin: 0;
  padding: 0.45rem 0.65rem;
  border-radius: var(--radius-sm);
  background: var(--status-info-bg);
  color: var(--status-info-text);
  font-size: 0.8rem;
  font-weight: 600;
}

.badge {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.55rem;
  border-radius: var(--radius-pill);
}

.badge--en_garita {
  background: var(--status-warn-bg);
  color: var(--status-warn-text);
}

.badge--entregado {
  background: var(--status-ok-bg);
  color: var(--status-ok-text);
}

.btn {
  min-block-size: 2.75rem;
  padding: 0.6rem 1rem;
  border-radius: var(--radius-sm);
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.btn--primary {
  background: var(--brand-600);
  color: var(--text-on-accent);
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
