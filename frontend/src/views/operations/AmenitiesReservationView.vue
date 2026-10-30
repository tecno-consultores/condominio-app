<script setup lang="ts">
import { onMounted, ref } from 'vue';
import {
  useAccessAmenitiesStore,
  type ResultadoInspeccionReserva,
} from '../../stores/accessAmenitiesStore';

const store = useAccessAmenitiesStore();

const areaNombre = ref('');
const areaAforo = ref<number>(50);
const areaCostoUsd = ref('25.00');
const areaDepositoUsd = ref('100.00');
const areaRequiereSolvencia = ref(true);

const reservaAreaId = ref<number>(1);
const reservaUnidadId = ref<number>(1);
const reservaFecha = ref('2026-12-20');
const reservaMotivo = ref('');

const feedbackExito = ref<string | null>(null);

onMounted(async () => {
  const areas = await store.fetchAreasSociales();
  const primera = areas[0];
  if (primera) {
    reservaAreaId.value = primera.id;
  }
  await store.fetchReservas();
});

async function handleCrearArea(): Promise<void> {
  feedbackExito.value = null;
  if (!areaNombre.value.trim()) {
    return;
  }
  try {
    const creada = await store.crearAreaSocial({
      nombre: areaNombre.value.trim(),
      aforo_maximo: Number(areaAforo.value),
      costo_uso_usd: areaCostoUsd.value.trim(),
      deposito_garantia_usd: areaDepositoUsd.value.trim(),
      requiere_solvencia_estricta: areaRequiereSolvencia.value,
    });
    reservaAreaId.value = creada.id;
    feedbackExito.value = `Área social "${creada.nombre}" configurada exitosamente.`;
    areaNombre.value = '';
  } catch {
    // Error expuesto reactivamente en store.error
  }
}

async function handleSolicitarReserva(): Promise<void> {
  feedbackExito.value = null;
  if (!reservaMotivo.value.trim()) {
    return;
  }
  try {
    const creada = await store.solicitarReservaArea({
      area_id: Number(reservaAreaId.value),
      unidad_id: Number(reservaUnidadId.value),
      fecha_evento: reservaFecha.value,
      motivo_evento: reservaMotivo.value.trim(),
    });
    feedbackExito.value = `Reserva #${creada.id} confirmada para ${creada.nombre_area} (${creada.fecha_evento}). Tarea de inspección post-evento #${creada.tarea_inspeccion_id ?? 'N/A'} asignada a conserjería.`;
    reservaMotivo.value = '';
  } catch {
    // Error expuesto reactivamente en store.error
  }
}

async function handleInspeccionar(
  reservaId: number,
  estado: ResultadoInspeccionReserva,
): Promise<void> {
  feedbackExito.value = null;
  const observacion =
    estado === 'FINALIZADA_SIN_DANOS'
      ? 'Instalaciones entregadas limpias y sin daños materiales.'
      : 'Se registraron observaciones o novedades durante la entrega del área.';
  try {
    const actualizada = await store.inspeccionarReserva(reservaId, {
      estado,
      observaciones_inspeccion: observacion,
    });
    feedbackExito.value = `Inspección post-evento registrada para Reserva #${actualizada.id} (${actualizada.estado}).`;
  } catch {
    // Error expuesto reactivamente en store.error
  }
}
</script>

<template>
  <section class="amenities-view" aria-labelledby="amenities-title">
    <header class="amenities-view__header">
      <h1 id="amenities-title" class="amenities-view__title">
        Reserva de Áreas Sociales y Amenidades
      </h1>
      <p class="amenities-view__subtitle">
        Gestión de Salón de Fiestas, Parrilleras y Áreas Recreativas vinculada a Solvencia Estricta
        e inspección automática de conserjería.
      </p>
    </header>

    <div
      id="solvency-gate-banner"
      class="solvency-banner"
      role="region"
      aria-label="Candado de Solvencia Estricta"
    >
      <strong>🔒 Candado de Solvencia Estricta ($0.00 USD):</strong>
      <span>
        Para reservar áreas sociales de uso exclusivo, la unidad solicitante debe encontrarse
        totalmente solvente sin recibos vencidos ni saldos parciales pendientes. Al confirmarse la
        reserva, el sistema agenda automáticamente una tarea de inspección post-evento al conserje.
      </span>
    </div>

    <div v-if="store.error" id="amenities-error-banner" class="alert alert--error" role="alert">
      {{ store.error }}
    </div>
    <div
      v-if="feedbackExito"
      id="amenities-success-banner"
      class="alert alert--success"
      role="status"
    >
      {{ feedbackExito }}
    </div>

    <section aria-label="Catálogo de áreas sociales disponibles">
      <h2 class="section-heading">
        Áreas Sociales Configuradas ({{ store.areasSociales.length }})
      </h2>

      <p v-if="store.areasSociales.length === 0" id="amenities-empty-state" class="empty-state">
        No hay áreas sociales registradas todavía.
      </p>

      <div class="cards-grid">
        <article
          v-for="area in store.areasSociales"
          :id="`amenity-card-${area.id}`"
          :key="area.id"
          class="card amenity-card"
        >
          <div class="amenity-card__top">
            <strong class="amenity-card__name">{{ area.nombre }}</strong>
            <span class="badge badge--solvencia">
              {{ area.requiere_solvencia_estricta ? 'Exige Solvencia $0.00' : 'Libre Acceso' }}
            </span>
          </div>
          <p class="amenity-card__meta">
            Aforo máx.: <strong>{{ area.aforo_maximo }} personas</strong> · Uso:
            <strong>${{ area.costo_uso_usd }} USD</strong> · Depósito en garantía:
            <strong>${{ area.deposito_garantia_usd }} USD</strong>
          </p>
        </article>
      </div>
    </section>

    <div class="forms-split">
      <form
        id="form-solicitar-reserva"
        class="card form-grid"
        aria-label="Solicitar reserva de área social"
        @submit.prevent="handleSolicitarReserva"
      >
        <h2 class="card__title">Solicitar Reserva Exclusiva por Fecha</h2>

        <div class="field-row">
          <label class="field" for="select-reserva-area">
            <span>Área Social</span>
            <select id="select-reserva-area" v-model.number="reservaAreaId">
              <option v-for="area in store.areasSociales" :key="area.id" :value="area.id">
                {{ area.nombre }} (Aforo {{ area.aforo_maximo }})
              </option>
              <option v-if="store.areasSociales.length === 0" :value="1">Área #1</option>
            </select>
          </label>

          <label class="field" for="input-reserva-unidad">
            <span>ID de Unidad Solicitante</span>
            <input
              id="input-reserva-unidad"
              v-model.number="reservaUnidadId"
              type="number"
              min="1"
              required
            />
          </label>
        </div>

        <div class="field-row">
          <label class="field" for="input-reserva-fecha">
            <span>Fecha del Evento</span>
            <input id="input-reserva-fecha" v-model="reservaFecha" type="date" required />
          </label>

          <label class="field" for="input-reserva-motivo">
            <span>Motivo o Tipo de Evento</span>
            <input
              id="input-reserva-motivo"
              v-model="reservaMotivo"
              type="text"
              minlength="5"
              maxlength="160"
              placeholder="Ej. Cumpleaños familiar infantil"
              required
            />
          </label>
        </div>

        <button
          id="btn-submit-reserva"
          type="submit"
          class="btn btn--primary"
          :disabled="store.isLoading"
        >
          {{
            store.isLoading ? 'Verificando Solvencia…' : 'Solicitar Reserva (Solvencia Estricta)'
          }}
        </button>
      </form>

      <form
        id="form-crear-area"
        class="card form-grid"
        aria-label="Configurar nueva área social"
        @submit.prevent="handleCrearArea"
      >
        <h2 class="card__title">Configurar Área Social (Directiva / Tesorería)</h2>

        <div class="field-row">
          <label class="field" for="input-area-nombre">
            <span>Nombre del Área Social</span>
            <input
              id="input-area-nombre"
              v-model="areaNombre"
              type="text"
              minlength="3"
              maxlength="100"
              placeholder="Ej. Salón de Fiestas Principal"
              required
            />
          </label>

          <label class="field" for="input-area-aforo">
            <span>Aforo Máximo (Personas)</span>
            <input
              id="input-area-aforo"
              v-model.number="areaAforo"
              type="number"
              min="1"
              max="500"
              required
            />
          </label>
        </div>

        <div class="field-row">
          <label class="field" for="input-area-costo">
            <span>Costo de Uso ($ USD)</span>
            <input id="input-area-costo" v-model="areaCostoUsd" type="text" required />
          </label>

          <label class="field" for="input-area-deposito">
            <span>Depósito en Garantía ($ USD)</span>
            <input id="input-area-deposito" v-model="areaDepositoUsd" type="text" required />
          </label>
        </div>

        <button
          id="btn-submit-area"
          type="submit"
          class="btn btn--secondary"
          :disabled="store.isLoading"
        >
          Registrar Área Social
        </button>
      </form>
    </div>

    <section aria-label="Calendario de reservas e inspección post-evento">
      <h2 class="section-heading">
        Calendario de Reservas e Inspección Post-Evento ({{ store.reservas.length }})
      </h2>

      <p v-if="store.reservas.length === 0" id="reservations-empty-state" class="empty-state">
        No hay reservas registradas en el calendario.
      </p>

      <div class="cards-grid">
        <article
          v-for="reserva in store.reservas"
          :id="`reservation-card-${reserva.id}`"
          :key="reserva.id"
          class="card reservation-card"
        >
          <div class="amenity-card__top">
            <div>
              <strong class="amenity-card__name">
                {{ reserva.nombre_area }} · Unidad {{ reserva.identificador_unidad }}
              </strong>
              <p class="amenity-card__meta">
                Fecha: <strong>{{ reserva.fecha_evento }}</strong> · {{ reserva.motivo_evento }}
              </p>
            </div>
            <span class="badge" :class="`badge--${reserva.estado.toLowerCase()}`">
              {{ reserva.estado }}
            </span>
          </div>

          <p v-if="reserva.observaciones_inspeccion" class="reservation-card__notes">
            Inspección: {{ reserva.observaciones_inspeccion }}
          </p>

          <div v-if="reserva.estado === 'CONFIRMADA'" class="reservation-card__actions">
            <button
              :id="`btn-inspect-ok-${reserva.id}`"
              type="button"
              class="btn btn--primary"
              @click="handleInspeccionar(reserva.id, 'FINALIZADA_SIN_DANOS')"
            >
              Inspección OK (Sin Daños)
            </button>
            <button
              :id="`btn-inspect-damage-${reserva.id}`"
              type="button"
              class="btn btn--danger"
              @click="handleInspeccionar(reserva.id, 'FINALIZADA_CON_DANOS')"
            >
              Reportar Daños Post-Evento
            </button>
          </div>
        </article>
      </div>
    </section>
  </section>
</template>

<style scoped>
.amenities-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.amenities-view__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.amenities-view__subtitle {
  color: #475569;
  font-size: 0.92rem;
  margin: 0.25rem 0 0;
}

.solvency-banner {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  background: #f0f9ff;
  border: 1px solid #0284c7;
  color: #0c4a6e;
  border-radius: 0.75rem;
  padding: 0.9rem 1.1rem;
  font-size: 0.88rem;
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

.forms-split {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr));
  gap: 1rem;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
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

.amenity-card,
.reservation-card {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.amenity-card__top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
}

.amenity-card__name {
  font-size: 0.98rem;
  color: #0f172a;
}

.amenity-card__meta {
  margin: 0.2rem 0 0;
  font-size: 0.85rem;
  color: #475569;
}

.reservation-card__notes {
  margin: 0;
  font-size: 0.84rem;
  color: #334155;
  background: #f8fafc;
  padding: 0.45rem 0.65rem;
  border-radius: 0.4rem;
}

.reservation-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.badge {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.55rem;
  border-radius: 9999px;
}

.badge--solvencia,
.badge--confirmada {
  background: #e0f2fe;
  color: #075985;
}

.badge--finalizada_sin_danos {
  background: #dcfce7;
  color: #14532d;
}

.badge--finalizada_con_danos {
  background: #fee2e2;
  color: #991b1b;
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

.btn--secondary {
  background: #0f172a;
  color: #ffffff;
}

.btn--danger {
  background: #b91c1c;
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
