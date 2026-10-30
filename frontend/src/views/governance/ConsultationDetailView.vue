<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import VoteReceiptModal from '../../components/governance/VoteReceiptModal.vue';
import { useAuthStore } from '../../stores/authStore';
import { useGovernanceStore } from '../../stores/governanceStore';
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

const canCloseConsultation = computed(() => {
  const rol = authStore.userRole;
  return (rol === 'PRESIDENTE' || rol === 'SECRETARIO') && consulta.value?.estado === 'ABIERTA';
});

const activeReceipt = computed(() => govStore.ultimoReciboVoto || consulta.value?.mi_voto || null);

onMounted(async () => {
  try {
    const detalle = await govStore.fetchConsultaDetalle(consultaId.value);
    if (detalle.opciones.length > 0 && selectedOpcionId.value === null) {
      selectedOpcionId.value = detalle.opciones[0].id;
    }
    if (opsStore.data.unidades.length > 0) {
      selectedUnidadId.value = opsStore.data.unidades[0].id;
    }
  } catch {
    // Error gestionado de forma no destructiva por governanceStore
  }
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
    closeSuccessMessage.value = `Consulta cerrada con estado ${res.estado}. Acta #${res.acta_bitacora_id} asentada en Bitácora.`;
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
      <header class="consultation-detail__card">
        <div class="consultation-detail__top">
          <div>
            <span class="consultation-detail__type">{{ consulta.tipo_consulta }}</span>
            <h1 id="detail-heading" class="consultation-detail__title">{{ consulta.titulo }}</h1>
          </div>
          <span id="badge-estado-consulta" class="consultation-detail__badge">
            {{ consulta.estado }}
          </span>
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
          📘 Acuerdo asentado en el Libro de Actas (Bitácora #{{ consulta.acta_bitacora_id }}).
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
            class="option-radio-card"
            :class="{ 'option-radio-card--selected': selectedOpcionId === op.id }"
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
            <label for="select-vote-unidad">ID de Unidad Inmobiliaria Representada</label>
            <input
              id="select-vote-unidad"
              v-model.number="selectedUnidadId"
              type="number"
              min="1"
              required
            />
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
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 1rem;
  padding: clamp(1rem, 2.5cqi, 1.5rem);
  box-shadow:
    0 4px 6px -1px rgba(15, 23, 42, 0.06),
    0 2px 4px -2px rgba(15, 23, 42, 0.04);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.consultation-detail__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.consultation-detail__type {
  font-size: 0.75rem;
  font-weight: 700;
  color: #0369a1;
}

.consultation-detail__title {
  margin: 0.2rem 0 0;
  font-size: clamp(1.25rem, 3cqi, 1.6rem);
  font-weight: 800;
  color: #0f172a;
  text-wrap: balance;
}

.consultation-detail__badge {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.25rem 0.65rem;
  border-radius: 9999px;
  background-color: #e0f2fe;
  color: #0369a1;
}

.consultation-detail__desc {
  margin: 0;
  font-size: 0.925rem;
  color: #334155;
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
  color: #475569;
}

progress.quorum-progress {
  appearance: none;
  border: 0 solid;
  overflow: clip;
  container-type: inline-size;
  inline-size: 100%;
  block-size: 0.75rem;
  --progress-bar-radius: 1e5px;
  --progress-bar-track: #e2e8f0;
  --progress-bar-fill: #0284c7;
  --progress-bar-indeterminate-size: 30%;
  --progress-bar-indeterminate-animation-duration: 1.5s;
  border-radius: var(--progress-bar-radius);
  background: var(--progress-bar-track);
  box-shadow: inset 0 1px 2px rgb(0 0 0 / 0.1);
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
  border-radius: 0.5rem;
  background-color: #f0f9ff;
  border: 1px solid #bae6fd;
  color: #0369a1;
  font-size: 0.85rem;
  font-weight: 600;
}

.consultation-detail__section-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
}

.consultation-detail__options {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.option-radio-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid #cbd5e1;
  background-color: #f8fafc;
  cursor: pointer;
}

.option-radio-card--selected {
  border-color: #0284c7;
  background-color: #f0f9ff;
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
  border-radius: 9999px;
  background-color: #dcfce7;
  color: #166534;
}

.option-radio-card__stats {
  font-size: 0.8rem;
  color: #475569;
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
  color: #334155;
}

.field input {
  padding: 0.55rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  font-size: 0.9rem;
  inline-size: 9rem;
}

.consultation-detail__receipt-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  background-color: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
  font-size: 0.875rem;
}

.consultation-detail__admin-footer {
  border-top: 1px solid #e2e8f0;
  padding-top: 0.85rem;
  display: flex;
  justify-content: flex-end;
}

.btn-primary,
.btn-secondary,
.btn-danger {
  padding: 0.55rem 1rem;
  border-radius: 0.5rem;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn-primary {
  background-color: #0284c7;
  color: #ffffff;
}

.btn-secondary {
  background-color: #0f172a;
  color: #ffffff;
}

.btn-danger {
  background-color: #b91c1c;
  color: #ffffff;
}

.banner {
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.banner--error {
  background-color: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
}

.banner--success {
  background-color: #dcfce7;
  color: #166534;
  border: 1px solid #86efac;
}

.tabular-num {
  font-variant-numeric: tabular-nums;
}

@media (pointer: coarse) {
  .btn-primary,
  .btn-secondary,
  .btn-danger {
    min-block-size: 2.75rem;
  }
}
</style>
