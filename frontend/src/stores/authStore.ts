import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { ApiError, apiRequest } from '../services/apiClient';

export type RolUsuario =
  | 'FANTASMA'
  | 'PROPIETARIO'
  | 'INQUILINO'
  | 'PRESIDENTE'
  | 'VICEPRESIDENTE'
  | 'TESORERO'
  | 'SECRETARIO'
  | 'VOCERO'
  | 'CONSERJE';

export interface UsuarioPerfil {
  id: number;
  nombre: string;
  cedula: string;
  correo: string;
  telefono: string;
  es_activo: boolean;
  rol: RolUsuario;
}

export interface RegistroPayload {
  nombre: string;
  cedula: string;
  correo: string;
  telefono: string;
  password: string;
  unidad_solicitada_id: number;
  tipo_ocupante_solicitado: 'PROPIETARIO' | 'INQUILINO';
}

export interface AsyncStoreState<T> {
  data: T | null;
  isLoading: boolean;
  isStale: boolean;
  errorMessage: string | null;
  lastUpdatedAt: number | null;
}

export const useAuthStore = defineStore('auth', () => {
  const data = ref<UsuarioPerfil | null>(null);
  const isLoading = ref<boolean>(false);
  const isStale = ref<boolean>(false);
  const errorMessage = ref<string | null>(null);
  const lastUpdatedAt = ref<number | null>(null);

  const isAuthenticated = computed<boolean>(() => data.value !== null);
  const isGhostUser = computed<boolean>(
    () => data.value !== null && (!data.value.es_activo || data.value.rol === 'FANTASMA'),
  );
  const isActiveUser = computed<boolean>(
    () => data.value !== null && data.value.es_activo && data.value.rol !== 'FANTASMA',
  );
  const userRole = computed<RolUsuario | null>(() => data.value?.rol ?? null);

  async function fetchProfile(): Promise<UsuarioPerfil | null> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const profile = await apiRequest<UsuarioPerfil>('/api/auth/me');
      data.value = profile;
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return profile;
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : new ApiError(0, 'Error inesperado');
      if (apiErr.status === 401) {
        data.value = null;
        isStale.value = false;
        errorMessage.value = apiErr.detail;
        return null;
      }
      // Regla Anti-Destructive Catch: ante fallos de red o 5xx conservamos los datos previos
      errorMessage.value = apiErr.detail;
      if (data.value !== null) {
        isStale.value = true;
      }
      return data.value;
    } finally {
      isLoading.value = false;
    }
  }

  async function login(correo: string, password: string): Promise<UsuarioPerfil | null> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      await apiRequest<{ message: string }>('/api/auth/login', {
        method: 'POST',
        body: { correo, password },
      });
      return await fetchProfile();
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : new ApiError(0, 'Error al iniciar sesión');
      errorMessage.value = apiErr.detail;
      throw apiErr;
    } finally {
      isLoading.value = false;
    }
  }

  async function register(
    payload: RegistroPayload,
    idempotencyKey: string,
  ): Promise<UsuarioPerfil> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const created = await apiRequest<UsuarioPerfil>('/api/auth/register', {
        method: 'POST',
        idempotencyKey,
        body: payload,
      });
      data.value = created;
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return created;
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : new ApiError(0, 'Error en el registro');
      errorMessage.value = apiErr.detail;
      throw apiErr;
    } finally {
      isLoading.value = false;
    }
  }

  function logout(): void {
    data.value = null;
    isStale.value = false;
    errorMessage.value = null;
    lastUpdatedAt.value = null;
  }

  function setProfileForTesting(profile: UsuarioPerfil | null): void {
    data.value = profile;
    isStale.value = false;
    errorMessage.value = null;
    lastUpdatedAt.value = profile ? Date.now() : null;
  }

  return {
    data,
    isLoading,
    isStale,
    errorMessage,
    lastUpdatedAt,
    isAuthenticated,
    isGhostUser,
    isActiveUser,
    userRole,
    fetchProfile,
    login,
    register,
    logout,
    setProfileForTesting,
  };
});
