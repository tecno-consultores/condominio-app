<script setup lang="ts">
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../../stores/authStore';
import { isSafeRedirectUrl } from '../../utils/security';

const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();

const correo = ref('');
const password = ref('');
const showPassword = ref(false);
const errorBanner = ref<string | null>(null);

function syncAriaInvalid(event: Event): void {
  const el = event.target as HTMLInputElement;
  el.setAttribute('aria-invalid', el.checkValidity() ? 'false' : 'true');
}

function syncAriaInvalidOnInput(event: Event): void {
  const el = event.target as HTMLInputElement | null;
  if (el && el.hasAttribute('aria-invalid')) {
    syncAriaInvalid(event);
  }
}

async function onSubmit(): Promise<void> {
  errorBanner.value = null;
  if (!correo.value.trim() || !password.value) {
    errorBanner.value = 'Por favor ingrese su correo electrónico y contraseña.';
    return;
  }
  try {
    const profile = await authStore.login(correo.value.trim(), password.value);
    if (!profile || !profile.es_activo || profile.rol === 'FANTASMA') {
      await router.push('/espera-aprobacion');
      return;
    }
    const redirectParam = typeof route.query?.redirect === 'string' ? route.query.redirect : null;
    const destino = isSafeRedirectUrl(redirectParam) ? (redirectParam as string) : '/dashboard';
    await router.push(destino);
  } catch {
    errorBanner.value = authStore.errorMessage || 'Credenciales inválidas.';
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-card" aria-labelledby="login-heading">
      <h1 id="login-heading" class="auth-card__title">Iniciar Sesión — Condominio App</h1>
      <p class="auth-card__subtitle">
        Acceda al estado de cobranza, reporte de pagos e incidencias de su comunidad.
      </p>

      <div v-if="errorBanner" id="login-error-banner" class="banner--error" role="alert">
        {{ errorBanner }}
      </div>

      <form id="login-form" class="auth-form" novalidate @submit.prevent="onSubmit">
        <div class="field">
          <label for="login-correo" class="field__label">Correo electrónico</label>
          <span id="login-correo-hint" class="field__hint">Ejemplo: vecino@condominio.com</span>
          <input
            id="login-correo"
            v-model="correo"
            name="email"
            type="email"
            autocomplete="username"
            spellcheck="false"
            enterkeyhint="next"
            required
            aria-describedby="login-correo-hint"
            class="field__input"
            @blur="syncAriaInvalid"
            @input="syncAriaInvalidOnInput"
          />
        </div>

        <div class="field">
          <div class="field__header">
            <label for="login-password" class="field__label">Contraseña</label>
            <button
              id="btn-toggle-password"
              type="button"
              class="field__toggle"
              :aria-pressed="showPassword"
              @click="showPassword = !showPassword"
            >
              {{ showPassword ? 'Ocultar' : 'Mostrar' }}
            </button>
          </div>
          <input
            id="login-password"
            v-model="password"
            name="password"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="current-password"
            enterkeyhint="done"
            required
            class="field__input"
            @blur="syncAriaInvalid"
            @input="syncAriaInvalidOnInput"
          />
        </div>

        <button
          id="btn-login-submit"
          type="submit"
          class="btn-primary"
          :disabled="authStore.isLoading"
          :aria-busy="authStore.isLoading"
        >
          {{ authStore.isLoading ? 'Verificando...' : 'Iniciar sesión' }}
        </button>
      </form>

      <p class="auth-card__footer">
        ¿Nuevo residente en el condominio?
        <router-link id="link-go-register" to="/register" class="auth-card__link">
          Solicitar registro de unidad
        </router-link>
      </p>
    </section>
  </main>
</template>

<style scoped>
.auth-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 1rem;
  background-color: #0f172a;
  color: #f8fafc;
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background-color: #1e293b;
  border: 1px solid #334155;
  border-radius: 0.75rem;
  padding: 1.75rem 1.5rem;
}

.auth-card__title {
  font-size: 1.35rem;
  margin: 0 0 0.5rem;
  color: #f8fafc;
}

.auth-card__subtitle {
  font-size: 0.875rem;
  color: #cbd5e1;
  margin: 0 0 1.25rem;
}

.banner--error {
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
  border-radius: 0.5rem;
  background-color: #450a0a;
  border: 1px solid #f87171;
  color: #fecaca;
  font-size: 0.875rem;
  font-weight: 600;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
}

.field__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field__label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #f1f5f9;
  margin-bottom: 0.25rem;
}

.field__hint {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-bottom: 0.35rem;
}

.field__toggle {
  background: transparent;
  border: none;
  color: #38bdf8;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0.25rem;
}

.field__input {
  padding: 0.65rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #475569;
  background-color: #0f172a;
  color: #f8fafc;
  font-size: 0.95rem;
}

.field__input:user-invalid {
  border-color: #f87171;
  background-color: #2a1215;
}

.field__input:user-valid {
  border-color: #34d399;
}

.btn-primary {
  margin-top: 0.5rem;
  min-height: 48px;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  border: none;
  background-color: #0284c7;
  color: #ffffff;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-card__footer {
  margin-top: 1.25rem;
  font-size: 0.85rem;
  color: #cbd5e1;
  text-align: center;
}

.auth-card__link {
  color: #38bdf8;
  font-weight: 600;
}
</style>
