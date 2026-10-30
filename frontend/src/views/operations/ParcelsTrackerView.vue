<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useAccessAmenitiesStore } from '../../stores/accessAmenitiesStore';

const store = useAccessAmenitiesStore();

const unidadId = ref<number>(1);
const empresaEnvio = ref('ZOOM');
const descripcion = ref('');
const urlFotoEvidencia = ref('');
const feedbackExito = ref<string | null>(null);

onMounted(async () => {
  await store.fetchPaqueteria();
});

async function handleRegistrarPaquete(): Promise<void> {
  feedbackExito.value = null;
  if (!descripcion.value.trim()) {
    return;
  }
  try {
    const creado = await store.registrarPaquete({
      unidad_id: Number(unidadId.value),
      empresa_envio: empresaEnvio.value.trim(),
      descripcion: descripcion.value.trim(),
      url_foto_evidencia: urlFotoEvidencia.value.trim() || null,
    });
    feedbackExito.value = `Encomienda #${creado.id} registrada para Unidad ${creado.identificador_unidad}.`;
    descripcion.value = '';
    urlFotoEvidencia.value = '';
  } catch {
    // Error expuesto reactivamente en store.error
  }
}

async function handleConfirmarEntrega(paqueteId: number): Promise<void> {
  feedbackExito.value = null;
  try {
    const actualizado = await store.confirmarEntregaPaquete(paqueteId);
    feedbackExito.value = `Paquete #${actualizado.id} marcado como ENTREGADO.`;
  } catch {
    // Error expuesto reactivamente en store.error
  }
}
</script>

<template>
  <section class="parcels-view" aria-labelledby="parcels-title">
    <header class="parcels-view__header">
      <h1 id="parcels-title" class="parcels-view__title">
        Control de Paquetería y Encomiendas en Garita
      </h1>
      <p class="parcels-view__subtitle">
        Cadena de custodia desde la recepción en conserjería hasta el retiro confirmado por la
        unidad.
      </p>
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
      id="form-registrar-paquete"
      class="card form-grid"
      aria-label="Registrar recepción de paquete en garita"
      @submit.prevent="handleRegistrarPaquete"
    >
      <h2 class="card__title">Recepción de Encomienda en Conserjería</h2>

      <div class="field-row">
        <label class="field" for="input-parcel-unidad">
          <span>ID de Unidad Destinataria</span>
          <input
            id="input-parcel-unidad"
            v-model.number="unidadId"
            type="number"
            min="1"
            required
          />
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
            placeholder="Ej. Caja sellada mediana con guía #99812"
            required
          />
        </label>

        <label class="field" for="input-parcel-foto">
          <span>URI de Evidencia Fotográfica (Opcional)</span>
          <input
            id="input-parcel-foto"
            v-model="urlFotoEvidencia"
            type="text"
            placeholder="s3://condominio-media/paquetes/foto.avif"
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

      <div class="cards-grid">
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

          <div class="parcel-card__actions">
            <button
              v-if="paquete.estado === 'EN_GARITA'"
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

.parcels-view__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.parcels-view__subtitle {
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

.card__title,
.section-heading {
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
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
  color: #1e293b;
}

.field input,
.field select {
  padding: 0.6rem 0.75rem;
  border: 1px solid #94a3b8;
  border-radius: 0.5rem;
  font-size: 0.92rem;
  color: #0f172a;
  background: #ffffff;
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
  color: #0f172a;
}

.parcel-card__desc {
  margin: 0.25rem 0 0;
  font-size: 0.86rem;
  color: #475569;
}

.badge {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.55rem;
  border-radius: 9999px;
}

.badge--en_garita {
  background: #fef3c7;
  color: #78350f;
}

.badge--entregado {
  background: #dcfce7;
  color: #14532d;
}

.btn {
  padding: 0.6rem 1rem;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.btn--primary {
  background: #0369a1;
  color: #ffffff;
}

.alert {
  padding: 0.8rem 1rem;
  border-radius: 0.5rem;
  font-weight: 600;
}

.alert--error {
  background: #fef2f2;
  border: 1px solid #ef4444;
  color: #991b1b;
}

.alert--success {
  background: #f0fdf4;
  border: 1px solid #22c55e;
  color: #14532d;
}

.empty-state {
  color: #475569;
  font-size: 0.9rem;
}
</style>
