import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../services/apiClient';
import { useAuthStore } from './authStore';
import { resolveStoreError } from './storeErrors';

describe('resolveStoreError — Separación estricta isStale vs mutaciones/4xx', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('marca isStale=true solo en GET con caché ante fallo de red o 5xx', async () => {
    const netGet = await resolveStoreError(new ApiError(0, 'Sin red'), 'Fallback', {
      isGetOperation: true,
      hasCachedData: true,
    });
    expect(netGet).toEqual({ unauthorized: false, isStale: true, message: 'Sin red' });

    const serverGet = await resolveStoreError(new ApiError(503, 'Caído'), 'Fallback', {
      isGetOperation: true,
      hasCachedData: true,
    });
    expect(serverGet).toEqual({ unauthorized: false, isStale: true, message: 'Caído' });
  });

  it('mantiene isStale=false en mutaciones, errores 4xx en GET y GET sin caché', async () => {
    const mutErr = await resolveStoreError(new ApiError(500, 'Fallo servidor'), 'Fallback', {
      isGetOperation: false,
      hasCachedData: true,
    });
    expect(mutErr.isStale).toBe(false);

    const client4xx = await resolveStoreError(new ApiError(404, 'No encontrado'), 'Fallback', {
      isGetOperation: true,
      hasCachedData: true,
    });
    expect(client4xx.isStale).toBe(false);

    const emptyCache = await resolveStoreError(new Error('Timeout'), 'Fallback', {
      isGetOperation: true,
      hasCachedData: false,
      useNativeErrorMessage: true,
    });
    expect(emptyCache).toEqual({ unauthorized: false, isStale: false, message: 'Timeout' });
  });

  it('delega HTTP 401 a authStore.handleUnauthorizedError sin marcar isStale', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 1,
      nombre: 'Ana',
      cedula: 'V-1',
      correo: 'a@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });

    const unauth = await resolveStoreError(new ApiError(401, 'Expirada'), 'Fallback', {
      isGetOperation: true,
      hasCachedData: true,
    });
    expect(unauth.unauthorized).toBe(true);
    expect(unauth.isStale).toBe(false);
    expect(authStore.isAuthenticated).toBe(false);
  });
});
