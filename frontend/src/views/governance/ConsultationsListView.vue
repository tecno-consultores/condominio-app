<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../../stores/authStore';
import {
  useGovernanceStore,
  type ReglaQuorum,
  type TipoConsulta,
} from '../../stores/governanceStore';

const authStore = useAuthStore();
const govStore = useGovernanceStore();
const router = useRouter();

const titulo = ref('');
const descripcionLegal = ref('');
const tipoConsulta = ref<TipoConsulta>('CARTA_CONSULTA_1RA');
const reglaQuorum = ref<ReglaQuorum>('DOS_TERCIOS');
const fechaCierre = ref('2026-12-31T23:59:00Z');
const opcionAfirmativa = ref('APROBAR PROPUESTA');
const opcionNegativa = ref('RECHAZAR PROPUESTA');
const createSuccessMessage = ref<string | null>(null);

const canCreateConsultation = computed(() => {
  const rol = authStore.userRole;
  return rol === 'PRESIDENTE' || rol === 'SECRETARIO';
});

onMounted(async () => {
  await govStore.fetchConsultas();
});

async function handleCreateConsulta(): Promise<void> {
  createSuccessMessage.value = null;
  try {
    const creada = await govStore.crearConsulta({
      titulo: titulo.value.trim(),
      descripcion_legal: descripcionLegal.value.trim(),
      tipo_consulta: tipoConsulta.value,
      regla_quorum: reglaQuorum.value,
      fecha_cierre: fechaCierre.value,
      opciones: [
        { etiqueta: opcionAfirmativa.value.trim(), es_opcion_aprobatoria: true },
        { etiqueta: opcionNegativa.value.trim(), es_opcion_aprobatoria: false },
      ],
    });
    createSuccessMessage.value = `Carta Consulta "${creada.titulo}" publicada exitosamente.`;
    titulo.value = '';
    descripcionLegal.value = '';
  } catch {
    // Error gestionado de forma no destructiva por governanceStore
  }
}

async function openConsultationDetail(id: number): Promise<void> {
  await router.push(`/consultas/${id}`);
}
</script>

<template>
  <section class="consultations-view" aria-labelledby="consultations-heading">
    <header class="consultations-view__header">
      <div>
        <span class="consultations-view__eyebrow">Gobernanza Digital — Art. 22, 23 y 24 LPH</span>
        <h1 id="consultations-heading" class="consultations-view__title">
          Cartas Consulta y Asambleas
        </h1>
      </div>
      <p class="consultations-view__subtitle">
        Cada unidad inmobiliaria ejerce un voto único ponderado por su porcentaje de alícuota con
        recibo criptográfico verificable <code>HMAC-SHA256</code>.
      </p>
    </header>

    <p v-if="govStore.error" class="banner banner--error" role="alert">
      {{ govStore.error }}
    </p>

    <p
      v-if="createSuccessMessage"
      id="banner-consulta-creada"
      class="banner banner--success"
      role="status"
    >
      {{ createSuccessMessage }}
    </p>

    <form
      v-if="canCreateConsultation"
      id="form-crear-consulta"
      class="consultations-view__form-card"
      @submit.prevent="handleCreateConsulta"
    >
      <h2 class="consultations-view__section-title">Convocar Nueva Carta Consulta o Asamblea</h2>

      <div class="consultations-view__grid">
        <div class="field">
          <label for="input-consulta-titulo">Título Formal de la Consulta</label>
          <input
            id="input-consulta-titulo"
            v-model="titulo"
            type="text"
            required
            minlength="5"
            placeholder="Ej. Carta Consulta #04-2026: Impermeabilización Torre A"
          />
        </div>

        <div class="field">
          <label for="select-tipo-consulta">Modalidad Legal (LPH)</label>
          <select id="select-tipo-consulta" v-model="tipoConsulta">
            <option value="CARTA_CONSULTA_1RA">Carta Consulta — 1ra Convocatoria (Art. 23)</option>
            <option value="CARTA_CONSULTA_2DA">Carta Consulta — 2da Convocatoria (Art. 23)</option>
            <option value="ASAMBLEA_ORDINARIA">Asamblea Ordinaria (Art. 24)</option>
            <option value="ASAMBLEA_EXTRAORDINARIA">Asamblea Extraordinaria (Art. 24)</option>
          </select>
        </div>

        <div class="field">
          <label for="select-regla-quorum">Regla de Quórum por Alícuota</label>
          <select id="select-regla-quorum" v-model="reglaQuorum">
            <option value="DOS_TERCIOS">Dos Tercios (66.6700% alícuota)</option>
            <option value="MAYORIA_SIMPLE">Mayoría Simple (50.0100% alícuota)</option>
            <option value="UNANIMIDAD">Unanimidad (100.0000% alícuota)</option>
          </select>
        </div>

        <div class="field">
          <label for="input-fecha-cierre">Fecha y Hora de Cierre (ISO UTC)</label>
          <input id="input-fecha-cierre" v-model="fechaCierre" type="text" required />
        </div>

        <div class="field">
          <label for="input-opcion-afirmativa">Opción Aprobatoria</label>
          <input id="input-opcion-afirmativa" v-model="opcionAfirmativa" type="text" required />
        </div>

        <div class="field">
          <label for="input-opcion-negativa">Opción de Rechazo</label>
          <input id="input-opcion-negativa" v-model="opcionNegativa" type="text" required />
        </div>
      </div>

      <div class="field">
        <label for="input-consulta-descripcion">Exposición de Motivos y Sustento Legal</label>
        <textarea
          id="input-consulta-descripcion"
          v-model="descripcionLegal"
          rows="3"
          required
          minlength="10"
          placeholder="Detalle el alcance técnico, presupuesto en USD y fundamento legal..."
        ></textarea>
      </div>

      <button
        id="btn-submit-consulta"
        type="submit"
        class="btn-primary"
        :disabled="govStore.isLoading"
      >
        Publicar Carta Consulta
      </button>
    </form>

    <div class="consultations-view__list">
      <article
        v-for="(consulta, idx) in govStore.consultas"
        :key="consulta.id"
        :data-testid="`consultation-card-${consulta.id}`"
        class="consultation-card"
      >
        <div class="consultation-card__top">
          <div>
            <span class="consultation-card__type">{{ consulta.tipo_consulta }}</span>
            <h2 class="consultation-card__title">{{ consulta.titulo }}</h2>
          </div>
          <span
            class="consultation-card__badge"
            :class="`consultation-card__badge--${consulta.estado.toLowerCase()}`"
          >
            {{ consulta.estado }}
          </span>
        </div>

        <p class="consultation-card__desc">{{ consulta.descripcion_legal }}</p>

        <div class="consultation-card__quorum">
          <div class="consultation-card__quorum-labels">
            <span :id="`quorum-label-${consulta.id}`">
              Quórum acumulado:
              <strong class="tabular-num">{{ consulta.participacion_alicuota }}%</strong>
              / Mínimo requerido ({{ consulta.regla_quorum }}):
              <strong class="tabular-num">{{ consulta.quorum_minimo_alicuota }}%</strong>
            </span>
            <span class="tabular-num">{{ consulta.total_votos }} unidades</span>
          </div>
          <progress
            :id="idx === 0 ? 'quorum-progress-bar' : `quorum-progress-bar-${consulta.id}`"
            class="quorum-progress"
            :value="Number(consulta.participacion_alicuota)"
            :max="100"
            :aria-labelledby="`quorum-label-${consulta.id}`"
          ></progress>
        </div>

        <footer class="consultation-card__footer">
          <span class="consultation-card__status-tag">
            {{
              consulta.ya_voto_usuario
                ? '✔ Voto de su unidad registrado'
                : 'Pendiente de votación de su unidad'
            }}
          </span>
          <button
            :id="`btn-open-consulta-${consulta.id}`"
            type="button"
            class="btn-secondary"
            @click="openConsultationDetail(consulta.id)"
          >
            Ver Detalle y Votar
          </button>
        </footer>
      </article>

      <p v-if="!govStore.consultas.length && !govStore.isLoading" class="consultations-view__empty">
        No existen Cartas Consulta ni Asambleas registradas actualmente.
      </p>
    </div>
  </section>
</template>

<style scoped>
.consultations-view {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.consultations-view__header {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.consultations-view__eyebrow {
  font-size: 0.75rem;
  font-weight: 700;
  color: #0369a1;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.consultations-view__title {
  margin: 0;
  font-size: clamp(1.35rem, 3cqi, 1.75rem);
  font-weight: 800;
  color: #0f172a;
  text-wrap: balance;
}

.consultations-view__subtitle {
  margin: 0;
  font-size: 0.925rem;
  color: #475569;
  max-inline-size: 65ch;
  text-wrap: pretty;
}

.consultations-view__form-card,
.consultation-card {
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

.consultations-view__section-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
}

.consultations-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr));
  gap: 0.85rem;
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

.field input,
.field select,
.field textarea {
  padding: 0.55rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #cbd5e1;
  font-size: 0.9rem;
  color: #0f172a;
  background-color: #ffffff;
}

.consultations-view__list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.consultation-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.consultation-card__type {
  font-size: 0.725rem;
  font-weight: 700;
  color: #0369a1;
}

.consultation-card__title {
  margin: 0.15rem 0 0;
  font-size: 1.1rem;
  font-weight: 800;
  color: #0f172a;
  text-wrap: balance;
}

.consultation-card__badge {
  font-size: 0.725rem;
  font-weight: 700;
  padding: 0.25rem 0.65rem;
  border-radius: 9999px;
  background-color: #e0f2fe;
  color: #0369a1;
}

.consultation-card__badge--cerrada_aprobada {
  background-color: #dcfce7;
  color: #15803d;
}

.consultation-card__badge--cerrada_rechazada,
.consultation-card__badge--cerrada_sin_quorum {
  background-color: #fee2e2;
  color: #b91c1c;
}

.consultation-card__desc {
  margin: 0;
  font-size: 0.9rem;
  color: #334155;
  max-inline-size: 65ch;
  text-wrap: pretty;
}

.consultation-card__quorum {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.consultation-card__quorum-labels {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.825rem;
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

.consultation-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
  border-top: 1px solid #e2e8f0;
  padding-top: 0.75rem;
}

.consultation-card__status-tag {
  font-size: 0.8rem;
  font-weight: 600;
  color: #475569;
}

.btn-primary,
.btn-secondary {
  padding: 0.55rem 1rem;
  border-radius: 0.5rem;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn-primary {
  align-self: flex-start;
  background-color: #0284c7;
  color: #ffffff;
}

.btn-secondary {
  background-color: #0f172a;
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

.consultations-view__empty {
  margin: 0;
  padding: 1.5rem;
  text-align: center;
  color: #64748b;
  background-color: #f8fafc;
  border-radius: 0.75rem;
  border: 1px dashed #cbd5e1;
}

.tabular-num {
  font-variant-numeric: tabular-nums;
}

@media (pointer: coarse) {
  .btn-primary,
  .btn-secondary {
    min-block-size: 2.75rem;
  }
}
</style>
