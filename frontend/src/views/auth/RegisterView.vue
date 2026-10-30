<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useIdempotency } from '../../composables/useIdempotency';
import { apiRequest } from '../../services/apiClient';
import { useAuthStore } from '../../stores/authStore';

interface UnidadItem {
  id: number;
  identificador: string;
  estructura_id: number;
}

const authStore = useAuthStore();
const router = useRouter();
const { isSubmitting, executeWithIdempotency, rotateKey } = useIdempotency();

const nombre = ref('');
const cedula = ref('');
const correo = ref('');
const telefono = ref('');
const password = ref('');
const unidadId = ref<number>(1);
const tipoOcupante = ref<'PROPIETARIO' | 'INQUILINO'>('PROPIETARIO');
const unidades = ref<UnidadItem[]>([{ id: 1, identificador: 'A-101', estructura_id: 1 }]);
const errorBanner = ref<string | null>(null);

onMounted(async () => {
  try {
    const lista = await apiRequest<UnidadItem[]>('/api/estructura/unidades');
    if (Array.isArray(lista) && lista.length > 0) {
      unidades.value = lista;
      unidadId.value = lista[0].id;
    }
  } catch {
    // Mantiene opción por defecto si la red falla al cargar el catálogo inicial
  }
});

function onFieldChange(): void {
  rotateKey();
}

async function onSubmit(): Promise<void> {
  errorBanner.value = null;
  if (!nombre.value.trim() || !cedula.value.trim() || !correo.value.trim() || !password.value) {
    errorBanner.value = 'Complete todos los campos obligatorios para solicitar su registro.';
    return;
  }
  try {
    await executeWithIdempotency(async (key) => {
      await authStore.register(
        {
          nombre: nombre.value.trim(),
          cedula: cedula.value.trim(),
          correo: correo.value.trim(),
          telefono: telefono.value.trim(),
          password: password.value,
          unidad_solicitada_id: Number(unidadId.value),
          tipo_ocupante_solicitado: tipoOcupante.value,
        },
        key,
      );
    });
    await router.push('/espera-aprobacion');
  } catch {
    errorBanner.value = authStore.errorMessage || 'No se pudo completar el registro.';
  }
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-card" aria-labelledby="register-heading">
      <h1 id="register-heading" class="auth-card__title">Registro de Residente</h1>
      <p class="auth-card__subtitle">
        Cree su cuenta. Quedará en espera hasta que el Presidente valide su unidad.
      </p>

      <div v-if="errorBanner" id="register-error-banner" class="banner--error" role="alert">
        {{ errorBanner }}
      </div>

      <form id="register-form" class="auth-form" novalidate @submit.prevent="onSubmit">
        <div class="field">
          <label for="reg-nombre" class="field__label">Nombre completo</label>
          <input
            id="reg-nombre"
            v-model="nombre"
            name="name"
            type="text"
            autocomplete="name"
            enterkeyhint="next"
            required
            class="field__input"
            @change="onFieldChange"
          />
        </div>

        <div class="field">
          <label for="reg-cedula" class="field__label">Documento de identidad (Cédula)</label>
          <input
            id="reg-cedula"
            v-model="cedula"
            name="cedula"
            type="text"
            enterkeyhint="next"
            required
            class="field__input"
            @change="onFieldChange"
          />
        </div>

        <div class="field">
          <label for="reg-correo" class="field__label">Correo electrónico</label>
          <input
            id="reg-correo"
            v-model="correo"
            name="email"
            type="email"
            autocomplete="username"
            spellcheck="false"
            enterkeyhint="next"
            required
            class="field__input"
            @change="onFieldChange"
          />
        </div>

        <div class="field">
          <label for="reg-telefono" class="field__label">Teléfono móvil</label>
          <input
            id="reg-telefono"
            v-model="telefono"
            name="tel"
            type="tel"
            autocomplete="tel"
            inputmode="tel"
            enterkeyhint="next"
            required
            class="field__input"
            @change="onFieldChange"
          />
        </div>

        <div class="field">
          <label for="reg-password" class="field__label">Contraseña nueva</label>
          <ul id="reg-password-rules" class="rules-list">
            <li>Mínimo 8 caracteres</li>
          </ul>
          <input
            id="reg-password"
            v-model="password"
            name="new-password"
            type="password"
            autocomplete="new-password"
            minlength="8"
            enterkeyhint="next"
            required
            aria-describedby="reg-password-rules"
            class="field__input"
          />
        </div>

        <div class="field">
          <label for="reg-unidad" class="field__label">Unidad solicitada</label>
          <select id="reg-unidad" v-model="unidadId" class="field__input">
            <option v-for="u in unidades" :key="u.id" :value="u.id">
              {{ u.identificador }}
            </option>
          </select>
        </div>

        <div class="field">
          <label for="reg-tipo-ocupante" class="field__label">Condición de ocupación</label>
          <select id="reg-tipo-ocupante" v-model="tipoOcupante" class="field__input">
            <option value="PROPIETARIO">Soy Propietario</option>
            <option value="INQUILINO">Soy Inquilino</option>
          </select>
        </div>

        <button
          id="btn-register-submit"
          type="submit"
          class="btn-primary"
          :disabled="isSubmitting"
          :aria-busy="isSubmitting"
        >
          {{ isSubmitting ? 'Enviando solicitud...' : 'Crear cuenta de residente' }}
        </button>
      </form>
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
  max-width: 460px;
  background-color: #1e293b;
  border: 1px solid #334155;
  border-radius: 0.75rem;
  padding: 1.75rem 1.5rem;
}

.auth-card__title {
  font-size: 1.35rem;
  margin: 0 0 0.5rem;
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
  gap: 0.875rem;
}

.field {
  display: flex;
  flex-direction: column;
}

.field__label {
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.rules-list {
  margin: 0 0 0.35rem;
  padding-left: 1.25rem;
  font-size: 0.75rem;
  color: #94a3b8;
}

.field:has(.field__input:user-invalid) .rules-list {
  color: #f87171;
  font-weight: 600;
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
</style>
