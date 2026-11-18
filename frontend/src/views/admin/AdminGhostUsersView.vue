<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import EmptyStateCard from '../../components/common/EmptyStateCard.vue';
import SkeletonCard from '../../components/common/SkeletonCard.vue';
import { useDualRefresh } from '../../composables/useDualRefresh';
import {
  useOperationsStore,
  type RolResidente,
  type TipoOcupante,
} from '../../stores/operationsStore';

const operationsStore = useOperationsStore();

interface PendingRowConfig {
  unidad_id: number;
  tipo_ocupante: TipoOcupante;
  rol: RolResidente;
  puede_votar_asamblea: boolean;
}

const rowConfigs = reactive<Record<number, PendingRowConfig>>({});
const successBanner = ref<string | null>(null);

const { isRefreshing, triggerRefresh } = useDualRefresh(() => operationsStore.fetchAdminData());

function getRowConfig(userId: number): PendingRowConfig {
  if (!rowConfigs[userId]) {
    rowConfigs[userId] = {
      unidad_id: operationsStore.data.unidades[0]?.id ?? 1,
      tipo_ocupante: 'PROPIETARIO',
      rol: 'PROPIETARIO',
      puede_votar_asamblea: true,
    };
  }
  return rowConfigs[userId];
}

function handleOcupanteChange(userId: number): void {
  const cfg = getRowConfig(userId);
  if (cfg.tipo_ocupante === 'INQUILINO') {
    cfg.puede_votar_asamblea = false;
    cfg.rol = 'INQUILINO';
    return;
  }
  if (cfg.rol === 'INQUILINO') {
    cfg.rol = 'PROPIETARIO';
  }
  cfg.puede_votar_asamblea = true;
}

onMounted(() => {
  void operationsStore.fetchAdminData();
});

async function handleActivateGhost(userId: number): Promise<void> {
  successBanner.value = null;
  const cfg = getRowConfig(userId);
  const canVote = cfg.tipo_ocupante === 'INQUILINO' ? false : cfg.puede_votar_asamblea;
  try {
    const activated = await operationsStore.asignarUsuarioFantasma(userId, {
      unidad_id: Number(cfg.unidad_id),
      tipo_ocupante: cfg.tipo_ocupante,
      rol: cfg.rol,
      puede_votar_asamblea: canVote,
    });
    successBanner.value = `Usuario "${activated.nombre}" activado con rol ${activated.rol}.`;
  } catch {
    // Error preservado en operationsStore.errorMessage
  }
}
</script>

<template>
  <section class="ghost-users" aria-labelledby="ghost-users-heading">
    <header class="ghost-users__header">
      <div>
        <h1 id="ghost-users-heading" class="ghost-users__title">
          Bandeja de Usuarios Fantasma Pendientes
        </h1>
        <p class="ghost-users__subtitle">
          Asigne el inmueble habitacional y el rol definitivo para liberar la cuenta del residente
          de su contención inicial.
        </p>
      </div>
      <button
        id="btn-dual-refresh"
        type="button"
        class="dual-refresh-btn"
        :disabled="isRefreshing || operationsStore.isLoading"
        @click="triggerRefresh"
      >
        <span aria-hidden="true">🔄</span>
        <span>{{ isRefreshing ? 'Actualizando...' : 'Refrescar' }}</span>
      </button>
    </header>

    <div
      v-if="operationsStore.errorMessage && !operationsStore.isStale"
      id="ghost-error-banner"
      class="ghost-users__alert ghost-users__alert--danger"
      role="alert"
    >
      {{ operationsStore.errorMessage }}
    </div>

    <div
      v-if="operationsStore.isStale && operationsStore.errorMessage"
      id="ghost-stale-banner"
      class="ghost-users__alert ghost-users__alert--warning"
      role="status"
    >
      {{ operationsStore.errorMessage }}
    </div>

    <div
      v-if="successBanner"
      id="ghost-success-banner"
      class="ghost-users__alert ghost-users__alert--success"
      role="status"
    >
      {{ successBanner }}
    </div>

    <SkeletonCard
      v-if="operationsStore.isLoading && operationsStore.data.usuariosPendientes.length === 0"
      :lines="3"
      height="120px"
      label="Cargando usuarios fantasma..."
    />
    <EmptyStateCard
      v-else-if="operationsStore.data.usuariosPendientes.length === 0"
      id="ghost-empty-state"
      class="ghost-users__empty empty-state"
      title="Bandeja sin solicitudes pendientes"
      description="No existen usuarios fantasma pendientes de asignación en este momento."
      icon="users"
    />

    <div v-else class="ghost-users__list">
      <article
        v-for="user in operationsStore.data.usuariosPendientes"
        :key="user.id"
        :data-testid="`ghost-user-card-${user.id}`"
        class="ghost-users__card"
      >
        <div class="ghost-users__info">
          <h2 class="ghost-users__name">{{ user.nombre }}</h2>
          <p class="ghost-users__meta">
            Cédula: <strong>{{ user.cedula }}</strong> · Correo: {{ user.correo }} · Tel:
            {{ user.telefono }}
          </p>
        </div>

        <div class="ghost-users__controls">
          <label :for="`select-unit-${user.id}`" class="ghost-users__label">
            Unidad
            <select
              :id="`select-unit-${user.id}`"
              v-model.number="getRowConfig(user.id).unidad_id"
              class="ghost-users__select"
            >
              <option v-for="u in operationsStore.data.unidades" :key="u.id" :value="u.id">
                {{ u.identificador }}
              </option>
            </select>
          </label>

          <label :for="`select-ocupante-${user.id}`" class="ghost-users__label">
            Ocupante
            <select
              :id="`select-ocupante-${user.id}`"
              v-model="getRowConfig(user.id).tipo_ocupante"
              class="ghost-users__select"
              @change="handleOcupanteChange(user.id)"
            >
              <option value="PROPIETARIO">PROPIETARIO</option>
              <option value="INQUILINO">INQUILINO</option>
            </select>
          </label>

          <label :for="`select-rol-${user.id}`" class="ghost-users__label">
            Rol RBAC
            <select
              :id="`select-rol-${user.id}`"
              v-model="getRowConfig(user.id).rol"
              class="ghost-users__select"
            >
              <option
                v-if="getRowConfig(user.id).tipo_ocupante !== 'INQUILINO'"
                value="PROPIETARIO"
              >
                PROPIETARIO
              </option>
              <option value="INQUILINO">INQUILINO</option>
              <option v-if="getRowConfig(user.id).tipo_ocupante !== 'INQUILINO'" value="VOCERO">
                VOCERO
              </option>
              <option v-if="getRowConfig(user.id).tipo_ocupante !== 'INQUILINO'" value="TESORERO">
                TESORERO
              </option>
              <option v-if="getRowConfig(user.id).tipo_ocupante !== 'INQUILINO'" value="SECRETARIO">
                SECRETARIO
              </option>
              <option value="CONSERJE">CONSERJE</option>
            </select>
          </label>

          <label :for="`check-votar-${user.id}`" class="ghost-users__checkbox">
            <input
              :id="`check-votar-${user.id}`"
              v-model="getRowConfig(user.id).puede_votar_asamblea"
              type="checkbox"
              :disabled="getRowConfig(user.id).tipo_ocupante === 'INQUILINO'"
            />
            <span>Voto en Asamblea (LPH)</span>
          </label>

          <button
            :id="`btn-activate-user-${user.id}`"
            type="button"
            class="ghost-users__btn"
            @click="handleActivateGhost(user.id)"
          >
            Vincular y Activar Cuenta
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.ghost-users {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.ghost-users__header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.ghost-users__title {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--text-primary);
}

.ghost-users__subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.ghost-users__alert {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 600;
}

.ghost-users__alert--danger {
  background-color: var(--status-danger-bg);
  border: 1px solid var(--status-danger-border);
  color: var(--status-danger-text);
}

.ghost-users__alert--warning {
  background-color: var(--status-warn-bg);
  border: 1px solid var(--status-warn-border);
  color: var(--status-warn-text);
}

.ghost-users__alert--success {
  background-color: var(--status-ok-bg);
  border: 1px solid var(--status-ok-border);
  color: var(--status-ok-text);
}

.ghost-users__empty {
  margin: 0;
  padding: 1.25rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-subtle);
  border: 1px dashed var(--border-subtle);
  color: var(--text-secondary);
  text-align: center;
}

.ghost-users__list {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.ghost-users__card {
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.ghost-users__name {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
}

.ghost-users__meta {
  margin: 0.25rem 0 0;
  font-size: 0.825rem;
  color: var(--text-secondary);
}

.ghost-users__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.75rem;
}

.ghost-users__label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.775rem;
  font-weight: 700;
  color: var(--text-primary);
}

.ghost-users__select {
  min-block-size: 2.75rem;
  padding: 0.5rem 0.65rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-card);
  color: var(--text-primary);
  font-size: 0.85rem;
}

.ghost-users__checkbox {
  min-block-size: 2.75rem;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.825rem;
  font-weight: 600;
  color: var(--text-primary);
}

.ghost-users__btn {
  min-block-size: 2.75rem;
  padding: 0.55rem 0.95rem;
  border-radius: var(--radius-sm);
  border: none;
  background-color: var(--brand-600);
  color: var(--text-on-accent);
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
}
</style>
