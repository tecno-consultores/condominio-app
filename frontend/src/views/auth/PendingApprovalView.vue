<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import ContextualHelpModal from '../../components/layout/ContextualHelpModal.vue';
import { useAuthStore } from '../../stores/authStore';

const authStore = useAuthStore();
const router = useRouter();
const statusMessage = ref<string | null>(null);
const isHelpOpen = ref(false);

async function checkApprovalStatus(): Promise<void> {
  statusMessage.value = null;
  const profile = await authStore.fetchProfile();
  if (profile && profile.es_activo && profile.rol !== 'FANTASMA') {
    await router.push('/dashboard');
    return;
  }
  statusMessage.value =
    'Su solicitud continúa en espera de asignación de unidad por parte del Presidente.';
}

async function handleLogout(): Promise<void> {
  authStore.logout();
  await router.push('/login');
}
</script>

<template>
  <main class="lock-page">
    <section id="ghost-lock-screen" class="lock-card" aria-labelledby="ghost-lock-heading">
      <div class="lock-card__top-bar">
        <span class="lock-card__badge">Cuenta en Validación</span>
        <button
          id="btn-contextual-help"
          type="button"
          class="auth-help-btn"
          aria-label="Abrir ayuda de cuenta en validación"
          @click="isHelpOpen = true"
        >
          ?
        </button>
      </div>
      <h1 id="ghost-lock-heading" class="lock-card__title">
        Registro completado. Esperando validación de la Junta
      </h1>
      <p class="lock-card__description">
        Por seguridad residencial, el acceso a estados financieros, pagos e incidencias se activa
        únicamente cuando el Presidente o Vicepresidente verifica su unidad habitacional.
      </p>

      <div v-if="statusMessage" id="ghost-status-msg" class="lock-card__notice" role="status">
        {{ statusMessage }}
      </div>

      <div class="lock-card__actions">
        <button
          id="btn-refresh-status"
          type="button"
          class="btn-primary"
          :disabled="authStore.isLoading"
          @click="checkApprovalStatus"
        >
          Verificar estado de aprobación
        </button>

        <button id="btn-logout" type="button" class="btn-secondary" @click="handleLogout">
          Cerrar sesión
        </button>
      </div>
    </section>

    <ContextualHelpModal :open="isHelpOpen" path="/espera-aprobacion" @close="isHelpOpen = false" />
  </main>
</template>

<style scoped>
.lock-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 1rem;
  background-color: #0f172a;
  color: #f8fafc;
}

.lock-card {
  width: 100%;
  max-width: 480px;
  background-color: #1e293b;
  border: 1px solid #334155;
  border-radius: 0.75rem;
  padding: 2rem 1.5rem;
  text-align: center;
}

.lock-card__badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  background-color: #78350f;
  color: #fef3c7;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 1rem;
}

.lock-card__title {
  font-size: 1.35rem;
  margin: 0 0 0.75rem;
}

.lock-card__description {
  font-size: 0.9rem;
  color: #cbd5e1;
  line-height: 1.5;
  margin: 0 0 1.25rem;
}

.lock-card__notice {
  padding: 0.75rem;
  border-radius: 0.5rem;
  background-color: #0f172a;
  border: 1px solid #38bdf8;
  color: #bae6fd;
  font-size: 0.85rem;
  margin-bottom: 1.25rem;
}

.lock-card__actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.btn-primary {
  min-height: 48px;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background-color: #0284c7;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.btn-secondary {
  min-height: 48px;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #64748b;
  background: transparent;
  color: #e2e8f0;
  font-weight: 600;
  cursor: pointer;
}

.lock-card__top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.auth-help-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 2rem;
  block-size: 2rem;
  border-radius: 50%;
  border: 1px solid #334155;
  background-color: #0f172a;
  color: #38bdf8;
  font-size: 0.875rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.auth-help-btn:hover {
  background-color: #0284c7;
  color: #ffffff;
  border-color: #0284c7;
}

@media (pointer: coarse) {
  .auth-help-btn {
    inline-size: 2.75rem;
    block-size: 2.75rem;
  }
}
</style>
