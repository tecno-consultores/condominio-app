<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useIdempotency } from '../../composables/useIdempotency';
import { useOperationsStore, type TipoEstructura } from '../../stores/operationsStore';
import { compareDecimal, parseDecimal, roundDecimalHalfUp } from '../../utils/decimal';

const operationsStore = useOperationsStore();
const { currentKey, rotateKey } = useIdempotency();
const { currentKey: alicuotaKey, rotateKey: rotateAlicuotaKey } = useIdempotency();

const nombre = ref('');
const tipo = ref<TipoEstructura>('TORRE');
const identificadoresRaw = ref('');
const selectedUnidadId = ref(1);
const alicuotaValor = ref('10.0000');
const cuotaFijaUnidad = ref('');
const validationError = ref<string | null>(null);
const successBanner = ref<string | null>(null);

onMounted(async () => {
  await operationsStore.fetchAdminData();
  const firstUnit = operationsStore.data.unidades[0];
  if (firstUnit && !operationsStore.data.unidades.some((u) => u.id === selectedUnidadId.value)) {
    selectedUnidadId.value = firstUnit.id;
  }
});

async function handleGenerateStructure(): Promise<void> {
  validationError.value = null;
  successBanner.value = null;

  const cleanIdentificadores = identificadoresRaw.value
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0);

  if (nombre.value.trim().length < 2 || cleanIdentificadores.length === 0) {
    validationError.value =
      'Debe indicar un nombre de estructura válido y al menos un identificador de unidad.';
    return;
  }

  try {
    const res = await operationsStore.generarEstructura(
      {
        nombre: nombre.value.trim(),
        tipo: tipo.value,
        identificadores: cleanIdentificadores,
      },
      currentKey.value,
    );
    rotateKey();
    nombre.value = '';
    identificadoresRaw.value = '';
    successBanner.value = `Estructura "${res.nombre}" generada con ${res.unidades_creadas} unidades.`;
  } catch {
    // Error preservado en operationsStore.errorMessage
  }
}

async function handleUpdateAlicuota(): Promise<void> {
  validationError.value = null;
  successBanner.value = null;

  const rawAlicuota = String(alicuotaValor.value ?? '').trim();
  const parsedAlicuota = parseDecimal(rawAlicuota);
  if (
    !parsedAlicuota ||
    compareDecimal(rawAlicuota, '0') < 0 ||
    compareDecimal(rawAlicuota, '100') > 0
  ) {
    validationError.value = 'La alícuota debe ser un porcentaje válido entre 0.0000 y 100.0000.';
    return;
  }

  const rawCuotaFija = String(cuotaFijaUnidad.value ?? '').trim();
  if (rawCuotaFija) {
    const parsedCuota = parseDecimal(rawCuotaFija);
    if (!parsedCuota || compareDecimal(rawCuotaFija, '0') < 0) {
      validationError.value = 'La cuota fija debe ser un monto válido mayor o igual a cero.';
      return;
    }
  }

  try {
    const normalizedAlicuota = roundDecimalHalfUp(rawAlicuota, 4);
    const normalizedCuotaFija = rawCuotaFija ? roundDecimalHalfUp(rawCuotaFija, 2) : null;
    const updated = await operationsStore.actualizarAlicuotaUnidad(
      selectedUnidadId.value,
      {
        alicuota: normalizedAlicuota,
        cuota_fija_usd: normalizedCuotaFija,
      },
      alicuotaKey.value,
    );
    rotateAlicuotaKey();
    successBanner.value = `Unidad ${updated.identificador} actualizada (Alícuota: ${updated.alicuota ?? normalizedAlicuota}%).`;
  } catch {
    // Error preservado en operationsStore.errorMessage
  }
}
</script>

<template>
  <section class="admin-structure" aria-labelledby="admin-structure-heading">
    <header class="admin-structure__header">
      <h1 id="admin-structure-heading" class="admin-structure__title">
        Generador Dinámico de Estructura Física
      </h1>
      <p class="admin-structure__subtitle">
        Cree torres, bloques, manzanas o calles junto con sus unidades habitacionales de forma
        idempotente.
      </p>
    </header>

    <div
      v-if="operationsStore.errorMessage && !operationsStore.isStale"
      id="estructura-error-banner"
      class="admin-structure__alert admin-structure__alert--danger"
      role="alert"
    >
      {{ operationsStore.errorMessage }}
    </div>

    <div
      v-if="operationsStore.isStale && operationsStore.errorMessage"
      id="estructura-stale-banner"
      class="admin-structure__alert admin-structure__alert--warning"
      role="status"
    >
      {{ operationsStore.errorMessage }}
    </div>

    <div
      v-if="successBanner"
      id="estructura-success-banner"
      class="admin-structure__alert admin-structure__alert--success"
      role="status"
    >
      {{ successBanner }}
    </div>

    <form
      id="form-generar-estructura"
      class="admin-structure__form"
      novalidate
      @submit.prevent="handleGenerateStructure"
    >
      <div class="admin-structure__grid">
        <div class="admin-structure__field">
          <label for="input-est-nombre" class="admin-structure__label">
            Nombre de la Estructura
          </label>
          <input
            id="input-est-nombre"
            v-model="nombre"
            type="text"
            class="admin-structure__input"
            placeholder="Ej. Torre Norte"
          />
        </div>

        <div class="admin-structure__field">
          <label for="select-est-tipo" class="admin-structure__label">Tipo de Agrupación</label>
          <select id="select-est-tipo" v-model="tipo" class="admin-structure__input">
            <option value="TORRE">TORRE</option>
            <option value="BLOQUE">BLOQUE</option>
            <option value="MANZANA">MANZANA</option>
            <option value="CALLE">CALLE</option>
            <option value="EDIFICIO">EDIFICIO</option>
          </select>
        </div>
      </div>

      <div class="admin-structure__field">
        <label for="input-est-identificadores" class="admin-structure__label">
          Identificadores de Unidades (separados por coma)
        </label>
        <input
          id="input-est-identificadores"
          v-model="identificadoresRaw"
          type="text"
          class="admin-structure__input"
          placeholder="Ej. Apto 1-A, Apto 1-B, Apto 2-A"
        />
      </div>

      <p v-if="validationError" id="estructura-validation-error" class="admin-structure__error">
        {{ validationError }}
      </p>

      <button id="btn-submit-estructura" type="submit" class="admin-structure__submit">
        Generar Estructura y Unidades
      </button>
    </form>

    <form
      id="form-actualizar-alicuota"
      class="admin-structure__form"
      novalidate
      @submit.prevent="handleUpdateAlicuota"
    >
      <h2 class="admin-structure__section-title">
        Configurar Alícuota LPH y Cuota Fija por Unidad
      </h2>
      <div class="admin-structure__grid">
        <div class="admin-structure__field">
          <label for="select-alicuota-unidad" class="admin-structure__label">Unidad</label>
          <select
            id="select-alicuota-unidad"
            v-model.number="selectedUnidadId"
            class="admin-structure__input"
          >
            <option v-for="u in operationsStore.data.unidades" :key="u.id" :value="u.id">
              {{ u.identificador }}
            </option>
          </select>
        </div>

        <div class="admin-structure__field">
          <label for="input-alicuota-valor" class="admin-structure__label">
            Alícuota de Participación (%)
          </label>
          <input
            id="input-alicuota-valor"
            v-model="alicuotaValor"
            type="number"
            step="0.0001"
            class="admin-structure__input"
            placeholder="Ej. 12.5000"
          />
        </div>

        <div class="admin-structure__field">
          <label for="input-cuota-fija-unidad" class="admin-structure__label">
            Cuota Fija Diferenciada (USD, opcional)
          </label>
          <input
            id="input-cuota-fija-unidad"
            v-model="cuotaFijaUnidad"
            type="number"
            step="0.01"
            class="admin-structure__input"
            placeholder="Ej. 25.00"
          />
        </div>
      </div>

      <button id="btn-submit-alicuota" type="submit" class="admin-structure__submit">
        Guardar Alícuota / Cuota Fija
      </button>
    </form>

    <section class="admin-structure__units" aria-label="Unidades registradas">
      <h2 class="admin-structure__section-title">
        Unidades Registradas ({{ operationsStore.data.unidades.length }})
      </h2>
      <ul id="unidades-list" class="admin-structure__unit-list">
        <li
          v-for="u in operationsStore.data.unidades"
          :key="u.id"
          class="admin-structure__unit-chip"
        >
          <strong>{{ u.identificador }}</strong>
          <span v-if="u.alicuota"> ({{ u.alicuota }}%)</span>
        </li>
      </ul>
    </section>
  </section>
</template>

<style scoped>
.admin-structure {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.admin-structure__title {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--text-primary);
}

.admin-structure__subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.admin-structure__alert {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 600;
}

.admin-structure__alert--danger {
  background-color: var(--status-danger-bg);
  border: 1px solid var(--status-danger-border);
  color: var(--status-danger-text);
}

.admin-structure__alert--warning {
  background-color: var(--status-warn-bg);
  border: 1px solid var(--status-warn-border);
  color: var(--status-warn-text);
}

.admin-structure__alert--success {
  background-color: var(--status-ok-bg);
  border: 1px solid var(--status-ok-border);
  color: var(--status-ok-text);
}

.admin-structure__form {
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.admin-structure__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
}

.admin-structure__field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.admin-structure__label {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-primary);
}

.admin-structure__input {
  min-block-size: 2.75rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-card);
  color: var(--text-primary);
  font-size: 0.875rem;
}

.admin-structure__error {
  margin: 0;
  color: var(--status-danger-text);
  font-size: 0.825rem;
  font-weight: 600;
}

.admin-structure__submit {
  min-block-size: 2.75rem;
  align-self: flex-start;
  padding: 0.625rem 1rem;
  border-radius: var(--radius-sm);
  border: none;
  background-color: var(--brand-600);
  color: var(--text-on-accent);
  font-weight: 700;
  cursor: pointer;
}

.admin-structure__section-title {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
}

.admin-structure__unit-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.admin-structure__unit-chip {
  padding: 0.4rem 0.75rem;
  border-radius: var(--radius-pill);
  background-color: var(--surface-subtle);
  border: 1px solid var(--border-subtle);
  font-size: 0.825rem;
  color: var(--text-primary);
}
</style>
