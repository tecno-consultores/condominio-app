import { computed, ref } from 'vue';
import { defineStore, getActivePinia } from 'pinia';
import type { Router } from 'vue-router';
import {
  ApiError,
  apiRequest,
  registerUnauthorizedCallback,
  resetCsrfToken,
} from '../services/apiClient';
import { isSafeRedirectUrl } from '../utils/security';

let boundRouter: Router | null = null;
const resettersByPinia = new WeakMap<object, Set<() => void>>();

export function registerAuthRouter(router: Router): void {
  boundRouter = router;
}

export function registerSessionResetter(resetFn: () => void): void {
  const activePinia = getActivePinia();
  if (!activePinia) {
    return;
  }
  let group = resettersByPinia.get(activePinia);
  if (!group) {
    group = new Set<() => void>();
    resettersByPinia.set(activePinia, group);
  }
  group.add(resetFn);
}

function runRegisteredResetters(): void {
  const activePinia = getActivePinia();
  if (!activePinia) {
    return;
  }
  const group = resettersByPinia.get(activePinia);
  if (!group) {
    return;
  }
  for (const resetFn of group) {
    resetFn();
  }
}

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
  unidad_activa_id?: number | null;
}

export interface AuthSessionResponse {
  message: string;
  rol: RolUsuario;
  csrf_token: string;
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

function isValidProfilePayload(payload: unknown): payload is UsuarioPerfil {
  return (
    Boolean(payload) &&
    typeof payload === 'object' &&
    typeof (payload as UsuarioPerfil).id === 'number' &&
    typeof (payload as UsuarioPerfil).rol === 'string'
  );
}

export const useAuthStore = defineStore('auth', () => {
  const data = ref<UsuarioPerfil | null>(null);
  const isLoading = ref<boolean>(false);
  const isStale = ref<boolean>(false);
  const errorMessage = ref<string | null>(null);
  const lastUpdatedAt = ref<number | null>(null);
  const sessionHydrated = ref<boolean>(false);
  const rbacNotice = ref<string | null>(null);

  const isAuthenticated = computed<boolean>(() => data.value !== null);
  const isGhostUser = computed<boolean>(
    () => data.value !== null && (!data.value.es_activo || data.value.rol === 'FANTASMA'),
  );
  const isActiveUser = computed<boolean>(
    () => data.value !== null && data.value.es_activo && data.value.rol !== 'FANTASMA',
  );
  const userRole = computed<RolUsuario | null>(() => data.value?.rol ?? null);
  const activeUnitId = computed<number | null>(() => data.value?.unidad_activa_id ?? null);

  function clearSession(): void {
    data.value = null;
    isStale.value = false;
    errorMessage.value = null;
    lastUpdatedAt.value = null;
    rbacNotice.value = null;
    sessionHydrated.value = true;
    resetCsrfToken();
    runRegisteredResetters();
  }

  async function fetchProfile(): Promise<UsuarioPerfil | null> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      const profile = await apiRequest<UsuarioPerfil>('/api/auth/me');
      if (!isValidProfilePayload(profile)) {
        clearSession();
        return null;
      }
      data.value = profile;
      isStale.value = false;
      lastUpdatedAt.value = Date.now();
      return profile;
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : new ApiError(0, 'Error inesperado');
      if (apiErr.status === 401) {
        clearSession();
        return null;
      }
      errorMessage.value = apiErr.detail;
      if (data.value !== null && (apiErr.status === 0 || apiErr.status >= 500)) {
        isStale.value = true;
      }
      return data.value;
    } finally {
      sessionHydrated.value = true;
      isLoading.value = false;
    }
  }

  async function login(correo: string, password: string): Promise<UsuarioPerfil | null> {
    isLoading.value = true;
    errorMessage.value = null;
    try {
      await apiRequest<AuthSessionResponse>('/api/auth/login', {
        method: 'POST',
        body: { correo, password },
      });
      const profile = await fetchProfile();
      sessionHydrated.value = true;
      return profile;
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
      sessionHydrated.value = true;
      return created;
    } catch (err) {
      const apiErr = err instanceof ApiError ? err : new ApiError(0, 'Error en el registro');
      errorMessage.value = apiErr.detail;
      throw apiErr;
    } finally {
      isLoading.value = false;
    }
  }

  function setRbacNotice(message: string | null): void {
    rbacNotice.value = message;
  }

  async function logout(): Promise<void> {
    try {
      // Enviar POST /api/auth/logout antes de limpiar CSRF/stores para revocar la sesión en KeyDB
      await apiRequest('/api/auth/logout', { method: 'POST' });
    } catch {
      // Garantizamos limpieza local aunque la red falle durante el cierre de sesión
    } finally {
      clearSession();
    }
  }

  async function handleUnauthorizedError(err: unknown): Promise<boolean> {
    if (!(err instanceof ApiError) || err.status !== 401) {
      return false;
    }
    const wasAuthenticated = data.value !== null;
    clearSession();
    errorMessage.value = 'Su sesión ha expirado. Inicie sesión nuevamente.';
    if (boundRouter) {
      const currentRoute = boundRouter.currentRoute.value;
      const currentPath = currentRoute.path;
      const currentFullPath = currentRoute.fullPath || currentPath;
      if (currentPath !== '/login' && currentPath !== '/register') {
        if (
          wasAuthenticated &&
          currentPath !== '/dashboard' &&
          currentPath !== '/espera-aprobacion' &&
          isSafeRedirectUrl(currentFullPath)
        ) {
          await boundRouter.push({ path: '/login', query: { redirect: currentFullPath } });
        } else {
          await boundRouter.push('/login');
        }
      }
    }
    return true;
  }

  registerUnauthorizedCallback(async (err) => {
    if (data.value !== null) {
      await handleUnauthorizedError(err);
    } else {
      clearSession();
    }
  });

  function setProfileForTesting(profile: UsuarioPerfil | null): void {
    data.value = profile;
    isStale.value = false;
    errorMessage.value = null;
    lastUpdatedAt.value = profile ? Date.now() : null;
    sessionHydrated.value = true;
  }

  return {
    data,
    isLoading,
    isStale,
    errorMessage,
    lastUpdatedAt,
    sessionHydrated,
    rbacNotice,
    isAuthenticated,
    isGhostUser,
    isActiveUser,
    userRole,
    activeUnitId,
    fetchProfile,
    login,
    register,
    setRbacNotice,
    clearSession,
    logout,
    handleUnauthorizedError,
    setProfileForTesting,
  };
});
