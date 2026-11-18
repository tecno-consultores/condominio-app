<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import VoteReceiptModal from '../../components/governance/VoteReceiptModal.vue';
import { useDualRefresh } from '../../composables/useDualRefresh';
import { getActiveConsultationTransition } from '../../composables/useViewTransition';
import { useAuthStore } from '../../stores/authStore';
import { useGovernanceStore, type EstadoConsulta } from '../../stores/governanceStore';
import { useOperationsStore } from '../../stores/operationsStore';

const route = useRoute();
const authStore = useAuthStore();
const govStore = useGovernanceStore();
const opsStore = useOperationsStore();

const selectedUnidadId = ref<number>(1);
const selectedOpcionId = ref<number | null>(null);
const showReceiptModal = ref(false);
const closeSuccessMessage = ref<string | null>(null);

const consultaId = computed(() => Number(route.params.id || 1));
const consulta = computed(() => govStore.consultaActual);

const STATUS_BADGE_MAP: Record<EstadoConsulta, { symbol: string; modifier: string }> = {
  ABIERTA: { symbol: '●', modifier: 'abierta' },
  CERRADA_APROBADA: { symbol: '✓', modifier: 'cerrada_aprobada' },
  CERRADA_RECHAZADA: { symbol: '✕', modifier: 'cerrada_rechazada' },
  CERRADA_SIN_QUORUM: { symbol: '!', modifier: 'cerrada_sin_quorum' },
};

const badgeMeta = computed(() => {
  const estado = consulta.value?.estado;
  if (!estado) {
    return { symbol: '!', modifier: 'cerrada_sin_quorum' };
  }
  return STATUS_BADGE_MAP[estado] ?? { symbol: '!', modifier: 'cerrada_sin_quorum' };
});

const canCloseConsultation = computed(() => {
  const rol = authStore.userRole;
  return (rol === 'PRESIDENTE' || rol === 'SECRETARIO') && consulta.value?.estado === 'ABIERTA';
});

const isTransitionTarget = computed(
  () => consulta.value !== null && getActiveConsultationTransition() === consulta.value.id,
);

const activeReceipt = computed(() => govStore.ultimoReciboVoto || consulta.value?.mi_voto || null);

async function refreshConsultationData(): Promise<void> {
  const [detailRes] = await Promise.allSettled([
    govStore.fetchConsultaDetalle(consultaId.value),
    opsStore.fetchUnidades(),
  ]);
  if (detailRes.status === 'fulfilled') {
    const detalle = detailRes.value;
    if (detalle.opciones.length > 0 && selectedOpcionId.value === null) {
      selectedOpcionId.value = detalle.opciones[0].id;
    }
  }
  if (authStore.activeUnitId !== null) {
    selectedUnidadId.value = authStore.activeUnitId;
  } else if (opsStore.data.unidades.length > 0) {
    selectedUnidadId.value = opsStore.data.unidades[0].id;
  }
}

const { isRefreshing, triggerRefresh } = useDualRefresh(refreshConsultationData);

onMounted(async () => {
  await refreshConsultationData();
});

async function handleCastVote(): Promise<void> {
  if (!consulta.value || selectedOpcionId.value === null) return;
  try {
    await govStore.votarConsulta(consulta.value.id, {
      unidad_id: Number(selectedUnidadId.value),
      opcion_id: Number(selectedOpcionId.value),
    });
    showReceiptModal.value = true;
  } catch {
    // Error gestionado de forma no destructiva por governanceStore
  }
}

async function handleCloseConsultation(): Promise<void> {
  if (!consulta.value) return;
  closeSuccessMessage.value = null;
  try {
    const res = await govStore.cerrarConsulta(consulta.value.id);
    closeSuccessMessage.value = `Consulta cerrada con estado ${res.estado}. Acta asentada en Bitácora oficial.`;
  } catch {
    // Error gestionado de forma no destructiva por governanceStore
  }
}
</script>

<template>
  <section class="consultation-detail" aria-labelledby="detail-heading">
    <p v-if="govStore.error" class="banner banner--error" role="alert">
      {{ govStore.error }}
    </p>

    <p
      v-if="closeSuccessMessage"
      id="banner-consulta-cerrada"
      class="banner banner--success"
      role="status"
    >
      {{ closeSuccessMessage }}
    </p>

    <template v-if="consulta">
      <header
        id="detail-consultation-hero"
        class="consultation-detail__card"
        :style="isTransitionTarget ? { viewTransitionName: 'active-consultation-card' } : undefined"
      >
        <div class="consultation-detail__top">
          <div>
            <span class="consultation-detail__type">{{ consulta.tipo_consulta }}</span>
            <h1 id="detail-heading" class="consultation-detail__title">{{ consulta.titulo }}</h1>
          </div>
          <div class="consultation-detail__top-actions">
            <button
              id="btn-dual-refresh"
              type="button"
              class="dual-refresh-btn"
              :disabled="isRefreshing || govStore.isLoading"
              @click="triggerRefresh"
            >
              <span aria-hidden="true">🔄</span>
              <span>{{ isRefreshing ? 'Actualizando...' : 'Refrescar' }}</span>
            </button>
            <span
              id="badge-estado-consulta"
              class="consultation-detail__badge"
              :class="`consultation-detail__badge--${badgeMeta.modifier}`"
            >
              <span aria-hidden="true">{{ badgeMeta.symbol }} </span>
              {{ consulta.estado }}
            </span>
          </div>
        </div>

        <p class="consultation-detail__desc">{{ consulta.descripcion_legal }}</p>

        <div class="consultation-detail__quorum">
          <div class="consultation-detail__quorum-row">
            <span id="detail-quorum-label">
              Participación escrutada:
              <strong id="detail-participacion-alicuota" class="tabular-num">
                {{ consulta.participacion_alicuota }}%
              </strong>
              · Umbral legal ({{ consulta.regla_quorum }}):
              <strong class="tabular-num">{{ consulta.quorum_minimo_alicuota }}%</strong>
            </span>
            <span class="tabular-num">{{ consulta.total_votos }} votos</span>
          </div>
          <progress
            id="quorum-progress-bar"
            class="quorum-progress"
            :value="Number(consulta.participacion_alicuota)"
            :max="100"
            aria-labelledby="detail-quorum-label"
          ></progress>
        </div>

        <div
          v-if="consulta.acta_bitacora_id"
          id="badge-acta-generada"
          class="consultation-detail__acta-banner"
        >
          📘 Acuerdo asentado en el Libro de Actas (Bitácora oficial).
        </div>
      </header>

      <div class="consultation-detail__card">
        <h2 class="consultation-detail__section-title">
          Opciones y Escrutinio Ponderado por Alícuota
        </h2>

        <div class="consultation-detail__options">
          <label
            v-for="op in consulta.opciones"
            :key="op.id"
            :data-testid="`option-card-${op.id}`"
            class="option-radio-card selectable-card"
            :class="{
              'option-radio-card--selected is-selected': selectedOpcionId === op.id,
            }"
          >
            <input
              :id="`radio-opcion-${op.id}`"
              v-model="selectedOpcionId"
              type="radio"
              name="opcion_consulta"
              :value="op.id"
              :disabled="consulta.estado !== 'ABIERTA' || consulta.ya_voto_usuario"
            />
            <div class="option-radio-card__body">
              <div class="option-radio-card__header">
                <strong>{{ op.etiqueta }}</strong>
                <span v-if="op.es_opcion_aprobatoria" class="option-radio-card__tag">
                  Opción Aprobatoria
                </span>
              </div>
              <span class="option-radio-card__stats tabular-num">
                {{ op.votos_cantidad }} unidades · {{ op.alicuota_acumulada }}% alícuota
              </span>
            </div>
          </label>
        </div>

        <form
          v-if="consulta.estado === 'ABIERTA' && !consulta.ya_voto_usuario"
          id="form-emitir-voto"
          class="consultation-detail__vote-form"
          @submit.prevent="handleCastVote"
        >
          <div class="field">
            <label for="select-vote-unidad">Unidad Inmobiliaria Representada</label>
            <select id="select-vote-unidad" v-model.number="selectedUnidadId" required>
              <option v-for="u in opsStore.data.unidades" :key="u.id" :value="u.id">
                {{ u.identificador }}
              </option>
            </select>
          </div>

          <button
            id="btn-cast-vote"
            type="submit"
            class="btn-primary"
            :disabled="govStore.isLoading || selectedOpcionId === null"
          >
            Emitir Voto Firmado (HMAC-SHA256)
          </button>
        </form>

        <div v-if="activeReceipt" class="consultation-detail__receipt-bar">
          <span>
            ✔ Voto inmutable registrado para la unidad
            <strong>{{ activeReceipt.identificador_unidad }}</strong>
            ({{ activeReceipt.alicuota_capturada }}% alícuota).
          </span>
          <button
            id="btn-open-vote-receipt"
            type="button"
            class="btn-secondary"
            @click="showReceiptModal = true"
          >
            Ver Recibo Criptográfico
          </button>
        </div>

        <footer v-if="canCloseConsultation" class="consultation-detail__admin-footer">
          <button
            id="btn-close-consultation"
            type="button"
            class="btn-danger"
            :disabled="govStore.isLoading"
            @click="handleCloseConsultation"
          >
            Cerrar Consulta y Generar Acta en Bitácora
          </button>
        </footer>
      </div>
    </template>

    <VoteReceiptModal
      :open="showReceiptModal"
      :recibo="activeReceipt"
      :titulo-consulta="consulta?.titulo"
      @close="showReceiptModal = false"
    />
  </section>
</template>

<style scoped>
.consultation-detail {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.consultation-detail__card {
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: clamp(1rem, 2.5cqi, 1.5rem);
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.consultation-detail__top {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.consultation-detail__top-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.625rem;
}

.consultation-detail__type {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--brand-accent);
}

.consultation-detail__title {
  margin: 0.2rem 0 0;
  font-size: clamp(1.25rem, 3cqi, 1.6rem);
  font-weight: 800;
  color: var(--text-primary);
  text-wrap: balance;
}

.consultation-detail__badge {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.25rem 0.65rem;
  border-radius: var(--radius-pill);
  background-color: var(--status-info-bg);
  color: var(--status-info-text);
}

.consultation-detail__badge--abierta {
  background-color: var(--status-info-bg);
  color: var(--status-info-text);
}

.consultation-detail__badge--cerrada_aprobada {
  background-color: var(--status-ok-bg);
  color: var(--status-ok-text);
}

.consultation-detail__badge--cerrada_rechazada,
.consultation-detail__badge--cerrada_sin_quorum {
  background-color: var(--status-danger-bg);
  color: var(--status-danger-text);
}

.consultation-detail__desc {
  margin: 0;
  font-size: 0.925rem;
  color: var(--text-secondary);
  max-inline-size: 65ch;
  text-wrap: pretty;
}

.consultation-detail__quorum {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.consultation-detail__quorum-row {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

progress.quorum-progress {
  appearance: none;
  border: 0 solid;
  overflow: clip;
  container-type: inline-size;
  inline-size: 100%;
  block-size: 0.75rem;
  --progress-bar-radius: 1e5px;
  --progress-bar-track: var(--border-subtle);
  --progress-bar-fill: var(--brand-600);
  --progress-bar-indeterminate-size: 30%;
  --progress-bar-indeterminate-animation-duration: 1.5s;
  border-radius: var(--progress-bar-radius);
  background: var(--progress-bar-track);
  box-shadow: var(--shadow-card);
}

@media (prefers-reduced-motion: reduce) {
  progress.quorum-progress {
    --progress-bar-indeterminate-animation-duration: 10s;
  }
}

progress.quorum-progress:dir(rtl) {
  --progress-bar-indeterminate-animation: progress-bar-indeterminate
    var(--progress-bar-indeterminate-animation-duration) infinite linear reverse;
}

progress.quorum-progress:indeterminate {
  --progress-bar-animation: var(
    --progress-bar-indeterminate-animation,
    progress-bar-indeterminate var(--progress-bar-indeterminate-animation-duration) infinite linear
  );
}

progress.quorum-progress::-webkit-progress-bar {
  background: transparent;
}

progress.quorum-progress::-webkit-progress-value {
  background: var(--progress-bar-fill);
  border-radius: var(--progress-bar-radius);
  transition: inline-size 0.3s;
  animation: var(--progress-bar-animation, revert-rule);
}

progress.quorum-progress::-moz-progress-bar {
  background: var(--progress-bar-fill);
  border-radius: var(--progress-bar-radius);
  transition: inline-size 0.3s;
  animation: var(--progress-bar-animation, revert-rule);
}

@keyframes progress-bar-indeterminate {
  from,
  to {
    inline-size: var(--progress-bar-indeterminate-size);
    margin-right: auto;
  }
  from {
    translate: -100%;
  }
  to {
    translate: 100cqi;
  }
}

.consultation-detail__acta-banner {
  padding: 0.65rem 0.85rem;
  border-radius: var(--radius-sm);
  background-color: var(--status-info-bg);
  border: 1px solid var(--status-info-border);
  color: var(--status-info-text);
  font-size: 0.85rem;
  font-weight: 600;
}

.consultation-detail__section-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary);
}

.consultation-detail__options {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.option-radio-card {
  min-block-size: 2.75rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background-color: var(--surface-subtle);
  cursor: pointer;
}

.option-radio-card--selected {
  border-color: var(--brand-600);
  background-color: var(--brand-tint);
}

.option-radio-card__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.option-radio-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.option-radio-card__tag {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-pill);
  background-color: var(--status-ok-bg);
  color: var(--status-ok-text);
}

.option-radio-card__stats {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.consultation-detail__vote-form {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 0.85rem;
  padding-top: 0.5rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.field label {
  font-size: 0.825rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.field select {
  min-block-size: 2.75rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-card);
  color: var(--text-primary);
  font-size: 0.9rem;
  min-inline-size: 12rem;
}

.consultation-detail__receipt-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  background-color: var(--status-ok-bg);
  border: 1px solid var(--status-ok-border);
  color: var(--status-ok-text);
  font-size: 0.875rem;
}

.consultation-detail__admin-footer {
  border-top: 1px solid var(--border-subtle);
  padding-top: 0.85rem;
  display: flex;
  justify-content: flex-end;
}

.btn-primary,
.btn-secondary,
.btn-danger {
  min-block-size: 2.75rem;
  padding: 0.55rem 1rem;
  border-radius: var(--radius-sm);
  font-weight: 700;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn-primary,
.btn-secondary {
  background-color: var(--brand-600);
  color: var(--text-on-accent);
}

.btn-danger {
  background-color: var(--status-danger-bg);
  border-color: var(--status-danger-border);
  color: var(--status-danger-text);
}

.banner {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 600;
}

.banner--error {
  background-color: var(--status-danger-bg);
  color: var(--status-danger-text);
  border: 1px solid var(--status-danger-border);
}

.banner--success {
  background-color: var(--status-ok-bg);
  color: var(--status-ok-text);
  border: 1px solid var(--status-ok-border);
}

.tabular-num {
  font-variant-numeric: tabular-nums;
}
</style>
