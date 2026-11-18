<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { ref } from 'vue';
import { useOperationsStore, type JuntaCargoRequestDTO } from '../../stores/operationsStore';

const operationsStore = useOperationsStore();

const usuarioId = ref('');
const cargo = ref<JuntaCargoRequestDTO['cargo']>('TESORERO');
const validationError = ref<string | null>(null);
const successBanner = ref<string | null>(null);

async function handleAssignBoardRole(): Promise<void> {
  validationError.value = null;
  successBanner.value = null;

  const rawUsuarioId = String(usuarioId.value ?? '').trim();
  const parsedId = Number.parseInt(rawUsuarioId, 10);
  if (!/^\d+$/.test(rawUsuarioId) || parsedId <= 0) {
    validationError.value = 'Debe especificar un identificador numérico de usuario válido.';
    return;
  }

  try {
    const updated = await operationsStore.asignarCargoJunta({
      usuario_id: parsedId,
      cargo: cargo.value,
    });
    successBanner.value = `Cargo ${updated.rol} asignado exitosamente a ${updated.nombre}.`;
    usuarioId.value = '';
  } catch {
    // Error preservado en operationsStore.errorMessage
  }
}
</script>

<template>
  <section class="board-roles" aria-labelledby="board-roles-heading">
    <header class="board-roles__header">
      <h1 id="board-roles-heading" class="board-roles__title">
        Gestión de Cargos de Junta de Condominio
      </h1>
      <p class="board-roles__subtitle">
        Exclusivo para Presidencia: asigne o revoque cargos directivos y de vocería sobre
        propietarios activos (los inquilinos quedan excluidos conforme a la LPH).
      </p>
    </header>

    <div
      v-if="operationsStore.errorMessage && !operationsStore.isStale"
      id="junta-error-banner"
      class="board-roles__alert board-roles__alert--warning"
      role="alert"
    >
      {{ operationsStore.errorMessage }}
    </div>

    <div
      v-if="successBanner"
      id="junta-success-banner"
      class="board-roles__alert board-roles__alert--success"
      role="status"
    >
      {{ successBanner }}
    </div>

    <form
      id="form-asignar-junta"
      class="board-roles__form"
      novalidate
      @submit.prevent="handleAssignBoardRole"
    >
      <div class="board-roles__grid">
        <div class="board-roles__field">
          <label for="input-junta-usuario-id" class="board-roles__label">
            Identificador del Propietario Activo
          </label>
          <input
            id="input-junta-usuario-id"
            v-model="usuarioId"
            type="number"
            min="1"
            step="1"
            class="board-roles__input"
            placeholder="Ej. 14"
          />
        </div>

        <div class="board-roles__field">
          <label for="select-junta-cargo" class="board-roles__label">Cargo en la Junta</label>
          <select id="select-junta-cargo" v-model="cargo" class="board-roles__input">
            <option value="PRESIDENTE">PRESIDENTE</option>
            <option value="VICEPRESIDENTE">VICEPRESIDENTE</option>
            <option value="TESORERO">TESORERO</option>
            <option value="SECRETARIO">SECRETARIO</option>
            <option value="VOCERO">VOCERO</option>
          </select>
        </div>
      </div>

      <p v-if="validationError" id="junta-validation-error" class="board-roles__error">
        {{ validationError }}
      </p>

      <button id="btn-submit-junta" type="submit" class="board-roles__submit">
        Asignar Cargo Directivo
      </button>
    </form>
  </section>
</template>

<style scoped>
.board-roles {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.board-roles__title {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--text-primary);
}

.board-roles__subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.board-roles__alert {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 600;
}

.board-roles__alert--warning {
  background-color: var(--status-warn-bg);
  border: 1px solid var(--status-warn-border);
  color: var(--status-warn-text);
}

.board-roles__alert--success {
  background-color: var(--status-ok-bg);
  border: 1px solid var(--status-ok-border);
  color: var(--status-ok-text);
}

.board-roles__form {
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.board-roles__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
}

.board-roles__field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.board-roles__label {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-primary);
}

.board-roles__input {
  min-block-size: 2.75rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-card);
  color: var(--text-primary);
  font-size: 0.875rem;
}

.board-roles__error {
  margin: 0;
  color: var(--status-danger-text);
  font-size: 0.825rem;
  font-weight: 600;
}

.board-roles__submit {
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
</style>
