<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import ContextualHelpModal from '../../components/layout/ContextualHelpModal.vue';
import ThemeToggleButton from '../../components/layout/ThemeToggleButton.vue';
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
        <div class="lock-card__top-actions">
          <ThemeToggleButton button-id="btn-theme-toggle" compact />
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
  background-color: var(--surface-canvas, #f8fafc);
  color: var(--text-primary, #0f172a);
}

.lock-card {
  width: 100%;
  max-width: 480px;
  background-color: var(--surface-card, #ffffff);
  border: 1px solid var(--border-subtle, #cbd5e1);
  border-block-start: 4px solid var(--status-warn-border, #d97706);
  border-radius: var(--radius-lg, 1rem);
  box-shadow: var(--surface-hairline), var(--shadow-elevated);
  padding: 2rem 1.5rem;
  text-align: center;
}

.lock-card__badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-pill, 9999px);
  background-color: var(--status-warn-bg, #fef3c7);
  color: var(--status-warn-text, #92400e);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
}

.lock-card__title {
  font-size: 1.35rem;
  margin: 0 0 0.75rem;
  color: var(--text-primary, #0f172a);
}

.lock-card__description {
  font-size: 0.9rem;
  color: var(--text-secondary, #475569);
  line-height: 1.5;
  margin: 0 0 1.25rem;
}

.lock-card__notice {
  padding: 0.75rem;
  border-radius: var(--radius-sm, 0.5rem);
  background-color: var(--status-info-bg, #f0f9ff);
  border: 1px solid var(--status-info-border, #0284c7);
  color: var(--status-info-text, #0369a1);
  font-size: 0.85rem;
  font-weight: 600;
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
  border-radius: var(--radius-sm, 0.5rem);
  border: none;
  background-color: var(--brand-600, #0369a1);
  color: #ffffff;
  font-weight: 700;
  box-shadow: var(--btn-raised-shadow);
  cursor: pointer;
  transition:
    transform 0.1s ease,
    box-shadow 0.15s ease;
}

.btn-primary:active:not(:disabled) {
  transform: translateY(1px);
  box-shadow: none;
}

.btn-secondary {
  min-height: 48px;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-sm, 0.5rem);
  border: 1px solid var(--border-control, #64748b);
  background: transparent;
  color: var(--text-primary, #0f172a);
  font-weight: 600;
  cursor: pointer;
}

.lock-card__top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.lock-card__top-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.auth-help-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 2.75rem;
  block-size: 2.75rem;
  border-radius: 50%;
  border: 1px solid var(--border-control, #64748b);
  background-color: var(--surface-card, #ffffff);
  color: var(--brand-accent, #0369a1);
  font-size: 0.9375rem;
  font-weight: 700;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease,
    border-color 0.15s ease;
}

.auth-help-btn:hover {
  background-color: var(--brand-600, #0369a1);
  color: #ffffff;
  border-color: var(--brand-600, #0369a1);
}
</style>
