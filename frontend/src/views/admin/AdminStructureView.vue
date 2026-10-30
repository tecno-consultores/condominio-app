<script setup lang="ts">
import { onMounted, ref } from 'vue';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import { useIdempotency } from '../../composables/useIdempotency';
import { useOperationsStore, type TipoEstructura } from '../../stores/operationsStore';

const operationsStore = useOperationsStore();
const { currentKey, rotateKey } = useIdempotency();

const nombre = ref('');
const tipo = ref<TipoEstructura>('TORRE');
const identificadoresRaw = ref('');
const validationError = ref<string | null>(null);
const successBanner = ref<string | null>(null);

onMounted(() => {
  void operationsStore.fetchAdminData();
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
</script>

<template>
  <AppShellLayout>
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
        v-if="operationsStore.isStale"
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
            <label for="input-est-nombre" class="admin-structure__label"
              >Nombre de la Estructura</label
            >
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
            <strong>#{{ u.id }}</strong> — {{ u.identificador }}
          </li>
        </ul>
      </section>
    </section>
  </AppShellLayout>
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
  color: #0f172a;
}

.admin-structure__subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: #475569;
}

.admin-structure__alert {
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.admin-structure__alert--warning {
  background-color: #fffbeb;
  border: 1px solid #f59e0b;
  color: #92400e;
}

.admin-structure__alert--success {
  background-color: #ecfdf5;
  border: 1px solid #10b981;
  color: #065f46;
}

.admin-structure__form {
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 0.875rem;
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
  color: #334155;
}

.admin-structure__input {
  padding: 0.55rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #94a3b8;
  font-size: 0.875rem;
}

.admin-structure__error {
  margin: 0;
  color: #b91c1c;
  font-size: 0.825rem;
  font-weight: 600;
}

.admin-structure__submit {
  align-self: flex-start;
  padding: 0.625rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background-color: #0284c7;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.admin-structure__section-title {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  font-weight: 700;
  color: #1e293b;
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
  border-radius: 9999px;
  background-color: #f1f5f9;
  border: 1px solid #cbd5e1;
  font-size: 0.825rem;
  color: #0f172a;
}
</style>
