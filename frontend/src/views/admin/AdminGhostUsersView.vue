<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import AppShellLayout from '../../components/layout/AppShellLayout.vue';
import type { RolUsuario } from '../../stores/authStore';
import { useOperationsStore, type TipoOcupante } from '../../stores/operationsStore';

const operationsStore = useOperationsStore();

interface PendingRowConfig {
  unidad_id: number;
  tipo_ocupante: TipoOcupante;
  rol: RolUsuario;
}

const rowConfigs = reactive<Record<number, PendingRowConfig>>({});
const successBanner = ref<string | null>(null);

function getRowConfig(userId: number): PendingRowConfig {
  if (!rowConfigs[userId]) {
    rowConfigs[userId] = {
      unidad_id: operationsStore.data.unidades[0]?.id ?? 1,
      tipo_ocupante: 'PROPIETARIO',
      rol: 'PROPIETARIO',
    };
  }
  return rowConfigs[userId];
}

onMounted(() => {
  void operationsStore.fetchAdminData();
});

async function handleActivateGhost(userId: number): Promise<void> {
  successBanner.value = null;
  const cfg = getRowConfig(userId);
  try {
    const activated = await operationsStore.asignarUsuarioFantasma(userId, {
      unidad_id: Number(cfg.unidad_id),
      tipo_ocupante: cfg.tipo_ocupante,
      rol: cfg.rol,
    });
    successBanner.value = `Usuario "${activated.nombre}" activado con rol ${activated.rol}.`;
  } catch {
    // Error preservado en operationsStore.errorMessage
  }
}
</script>

<template>
  <AppShellLayout>
    <section class="ghost-users" aria-labelledby="ghost-users-heading">
      <header class="ghost-users__header">
        <h1 id="ghost-users-heading" class="ghost-users__title">
          Bandeja de Usuarios Fantasma Pendientes
        </h1>
        <p class="ghost-users__subtitle">
          Asigne el inmueble habitacional y el rol definitivo para liberar la cuenta del residente
          de su contención inicial.
        </p>
      </header>

      <div
        v-if="operationsStore.isStale"
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

      <p
        v-if="operationsStore.data.usuariosPendientes.length === 0"
        id="ghost-empty-state"
        class="ghost-users__empty"
      >
        No existen usuarios fantasma pendientes de asignación en este momento.
      </p>

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
                <option value="PROPIETARIO">PROPIETARIO</option>
                <option value="INQUILINO">INQUILINO</option>
                <option value="VOCERO">VOCERO</option>
                <option value="TESORERO">TESORERO</option>
                <option value="SECRETARIO">SECRETARIO</option>
                <option value="CONSERJE">CONSERJE</option>
              </select>
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
  </AppShellLayout>
</template>

<style scoped>
.ghost-users {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.ghost-users__title {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
  color: #0f172a;
}

.ghost-users__subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: #475569;
}

.ghost-users__alert {
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.ghost-users__alert--warning {
  background-color: #fffbeb;
  border: 1px solid #f59e0b;
  color: #92400e;
}

.ghost-users__alert--success {
  background-color: #ecfdf5;
  border: 1px solid #10b981;
  color: #065f46;
}

.ghost-users__empty {
  margin: 0;
  padding: 1.25rem;
  border-radius: 0.875rem;
  background-color: #f8fafc;
  border: 1px dashed #cbd5e1;
  color: #64748b;
  text-align: center;
}

.ghost-users__list {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.ghost-users__card {
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 0.875rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.ghost-users__name {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}

.ghost-users__meta {
  margin: 0.25rem 0 0;
  font-size: 0.825rem;
  color: #475569;
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
  color: #334155;
}

.ghost-users__select {
  padding: 0.5rem 0.65rem;
  border-radius: 0.5rem;
  border: 1px solid #94a3b8;
  font-size: 0.85rem;
}

.ghost-users__btn {
  padding: 0.55rem 0.95rem;
  border-radius: 0.5rem;
  border: none;
  background-color: #0284c7;
  color: #ffffff;
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
}
</style>
