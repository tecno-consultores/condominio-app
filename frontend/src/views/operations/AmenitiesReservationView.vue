<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useDualRefresh } from '../../composables/useDualRefresh';
import {
  useAccessAmenitiesStore,
  type ReservaAreaDTO,
  type ResultadoInspeccionReserva,
} from '../../stores/accessAmenitiesStore';
import { useAuthStore } from '../../stores/authStore';
import { useOperationsStore } from '../../stores/operationsStore';
import { compareDecimal, parseDecimal, roundDecimalHalfUp } from '../../utils/decimal';

const authStore = useAuthStore();
const opsStore = useOperationsStore();
const store = useAccessAmenitiesStore();

const areaNombre = ref('');
const areaAforo = ref('50');
const areaCostoUsd = ref('25.00');
const areaDepositoUsd = ref('100.00');
const areaRequiereSolvencia = ref(true);

const reservaAreaId = ref<number>(1);
const reservaUnidadId = ref<number>(1);
const reservaFecha = ref('2026-12-20');
const reservaMotivo = ref('');

const feedbackExito = ref<string | null>(null);
const validationError = ref<string | null>(null);

const canManageAreas = computed(() => {
  const rol = authStore.userRole;
  return rol === 'PRESIDENTE' || rol === 'TESORERO';
});

const canInspectReservations = computed(() => {
  const rol = authStore.userRole;
  return rol === 'CONSERJE' || rol === 'PRESIDENTE' || rol === 'TESORERO';
});

function canCancelReservation(reserva: ReservaAreaDTO): boolean {
  const rol = authStore.userRole;
  const isBoardCanceller =
    rol === 'PRESIDENTE' || rol === 'VICEPRESIDENTE' || rol === 'TESORERO' || rol === 'SECRETARIO';
  return (
    isBoardCanceller ||
    (authStore.data?.id !== undefined && reserva.solicitante_id === authStore.data.id)
  );
}

async function refreshAmenitiesData(): Promise<void> {
  const [areasRes] = await Promise.allSettled([
    store.fetchAreasSociales(),
    store.fetchReservas(),
    opsStore.fetchUnidades(),
  ]);
  if (areasRes.status === 'fulfilled') {
    const primera = areasRes.value[0];
    if (primera) {
      reservaAreaId.value = primera.id;
    }
  }
  if (authStore.activeUnitId !== null) {
    reservaUnidadId.value = authStore.activeUnitId;
  } else if (
    opsStore.data.unidades.length > 0 &&
    !opsStore.data.unidades.some((u) => u.id === reservaUnidadId.value)
  ) {
    reservaUnidadId.value = opsStore.data.unidades[0].id;
  }
}

const { isRefreshing, triggerRefresh } = useDualRefresh(refreshAmenitiesData);

onMounted(async () => {
  await refreshAmenitiesData();
});

async function handleCrearArea(): Promise<void> {
  feedbackExito.value = null;
  validationError.value = null;
  if (!canManageAreas.value || !areaNombre.value.trim()) {
    return;
  }

  const rawAforo = String(areaAforo.value ?? '').trim();
  const parsedAforo = Number.parseInt(rawAforo, 10);
  if (!/^\d+$/.test(rawAforo) || parsedAforo < 1 || parsedAforo > 500) {
    validationError.value = 'El aforo máximo debe ser un entero entre 1 y 500 personas.';
    return;
  }

  const rawCosto = String(areaCostoUsd.value ?? '').trim();
  const rawDeposito = String(areaDepositoUsd.value ?? '').trim();
  if (
    !parseDecimal(rawCosto) ||
    compareDecimal(rawCosto, '0') < 0 ||
    !parseDecimal(rawDeposito) ||
    compareDecimal(rawDeposito, '0') < 0
  ) {
    validationError.value = 'El costo y depósito deben ser montos USD válidos.';
    return;
  }

  try {
    const creada = await store.crearAreaSocial({
      nombre: areaNombre.value.trim(),
      aforo_maximo: parsedAforo,
      costo_uso_usd: roundDecimalHalfUp(rawCosto, 2),
      deposito_garantia_usd: roundDecimalHalfUp(rawDeposito, 2),
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
  validationError.value = null;
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
    feedbackExito.value = `Reserva confirmada para ${creada.nombre_area} (${creada.fecha_evento}). Tarea de inspección post-evento asignada a conserjería.`;
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
  if (!canInspectReservations.value) {
    return;
  }
  const observacion =
    estado === 'FINALIZADA_SIN_DANOS'
      ? 'Instalaciones entregadas limpias y sin daños materiales.'
      : 'Se registraron observaciones o novedades durante la entrega del área.';
  try {
    const actualizada = await store.inspeccionarReserva(reservaId, {
      estado,
      observaciones_inspeccion: observacion,
    });
    feedbackExito.value = `Inspección post-evento registrada (${actualizada.estado}).`;
  } catch {
    // Error expuesto reactivamente en store.error
  }
}

async function handleCancelarReserva(reservaId: number): Promise<void> {
  feedbackExito.value = null;
  try {
    await store.cancelarReserva(reservaId);
    feedbackExito.value = 'Reserva cancelada exitosamente. La fecha quedó liberada.';
  } catch {
    // Error expuesto reactivamente en store.error
  }
}
</script>

<template>
  <section class="amenities-view" aria-labelledby="amenities-title">
    <header class="amenities-view__header">
      <div>
        <h1 id="amenities-title" class="amenities-view__title">
          Reserva de Áreas Sociales y Amenidades
        </h1>
        <p class="amenities-view__subtitle">
          Gestión de Salón de Fiestas, Parrilleras y Áreas Recreativas vinculada a Solvencia
          Estricta e inspección automática de conserjería.
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
    <div v-if="validationError" class="alert alert--error" role="alert">
      {{ validationError }}
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
              <option v-if="store.areasSociales.length === 0" :value="1">Salón social</option>
            </select>
          </label>

          <label class="field" for="input-reserva-unidad">
            <span>Unidad Solicitante</span>
            <select id="input-reserva-unidad" v-model.number="reservaUnidadId" required>
              <option v-for="u in opsStore.data.unidades" :key="u.id" :value="u.id">
                {{ u.identificador }}
              </option>
            </select>
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
        v-if="canManageAreas"
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
              v-model="areaAforo"
              type="number"
              min="1"
              max="500"
              step="1"
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
            <template v-if="canInspectReservations">
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
            </template>
            <button
              v-if="canCancelReservation(reserva)"
              :id="`btn-cancelar-reserva-${reserva.id}`"
              type="button"
              class="btn btn--secondary"
              @click="handleCancelarReserva(reserva.id)"
            >
              Cancelar Reserva
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

.amenities-view__header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.amenities-view__title {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.amenities-view__subtitle {
  color: var(--text-secondary);
  font-size: 0.92rem;
  margin: 0.25rem 0 0;
}

.solvency-banner {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  background: var(--status-info-bg);
  border: 1px solid var(--status-info-border);
  color: var(--status-info-text);
  border-radius: var(--radius-md);
  padding: 0.9rem 1.1rem;
  font-size: 0.88rem;
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
  color: var(--text-primary);
}

.amenity-card__meta {
  margin: 0.2rem 0 0;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.reservation-card__notes {
  margin: 0;
  font-size: 0.84rem;
  color: var(--text-secondary);
  background: var(--surface-subtle);
  padding: 0.45rem 0.65rem;
  border-radius: var(--radius-sm);
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
  border-radius: var(--radius-pill);
}

.badge--solvencia,
.badge--confirmada {
  background: var(--brand-tint);
  color: var(--brand-accent);
}

.badge--finalizada_sin_danos {
  background: var(--status-ok-bg);
  color: var(--status-ok-text);
}

.badge--finalizada_con_danos {
  background: var(--status-danger-bg);
  color: var(--status-danger-text);
}

.badge--cancelada {
  background: var(--surface-subtle);
  color: var(--text-secondary);
}

.btn {
  min-block-size: 2.75rem;
  padding: 0.6rem 1rem;
  border-radius: var(--radius-sm);
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn--primary,
.btn--secondary {
  background: var(--brand-600);
  color: var(--text-on-accent);
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
