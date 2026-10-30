import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useAuthStore, type UsuarioPerfil } from './authStore';
import * as apiClient from '../services/apiClient';

const PERFIL_ACTIVO: UsuarioPerfil = {
  id: 1,
  nombre: 'Carlos Pérez',
  cedula: 'V-12345678',
  correo: 'carlos@condominio.test',
  telefono: '+584141234567',
  es_activo: true,
  rol: 'PROPIETARIO',
};

const PERFIL_FANTASMA: UsuarioPerfil = {
  id: 9,
  nombre: 'Nuevo Vecino',
  cedula: 'V-99999999',
  correo: 'fantasma@condominio.test',
  telefono: '+584149999999',
  es_activo: false,
  rol: 'FANTASMA',
};

describe('Store useAuthStore (No Destructivo & Trimodal)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('inicia sesión, carga el perfil activo y calcula getters correctamente', async () => {
    const spy = vi
      .spyOn(apiClient, 'apiRequest')
      .mockResolvedValueOnce({ message: 'Login exitoso' })
      .mockResolvedValueOnce(PERFIL_ACTIVO);

    const store = useAuthStore();
    const res = await store.login('carlos@condominio.test', 'Password123!');

    expect(res).toEqual(PERFIL_ACTIVO);
    expect(store.isAuthenticated).toBe(true);
    expect(store.isActiveUser).toBe(true);
    expect(store.isGhostUser).toBe(false);
    expect(store.userRole).toBe('PROPIETARIO');
    expect(spy).toHaveBeenCalledTimes(2);
  });

  it('preserva los datos conocidos y marca isStale=true ante micro-cortes de red (Anti-Destructive Catch)', async () => {
    const store = useAuthStore();
    store.setProfileForTesting(PERFIL_ACTIVO);

    vi.spyOn(apiClient, 'apiRequest').mockRejectedValueOnce(
      new apiClient.ApiError(0, 'Sin conexión con el servidor'),
    );

    const res = await store.fetchProfile();
    expect(res).toEqual(PERFIL_ACTIVO);
    expect(store.data).toEqual(PERFIL_ACTIVO);
    expect(store.isStale).toBe(true);
    expect(store.errorMessage).toBe('Sin conexión con el servidor');

    // En cambio, un 401 explícito sí invalida la sesión
    vi.spyOn(apiClient, 'apiRequest').mockRejectedValueOnce(
      new apiClient.ApiError(401, 'Token expirado'),
    );
    const res401 = await store.fetchProfile();
    expect(res401).toBeNull();
    expect(store.data).toBeNull();
    expect(store.isStale).toBe(false);
  });

  it('registra un Usuario Fantasma con Idempotency-Key y permite cerrar sesión', async () => {
    vi.spyOn(apiClient, 'apiRequest').mockResolvedValueOnce(PERFIL_FANTASMA);
    const store = useAuthStore();

    const created = await store.register(
      {
        nombre: 'Nuevo Vecino',
        cedula: 'V-99999999',
        correo: 'fantasma@condominio.test',
        telefono: '+584149999999',
        password: 'Password123!',
        unidad_solicitada_id: 1,
        tipo_ocupante_solicitado: 'PROPIETARIO',
      },
      'idem-reg-001',
    );

    expect(created.es_activo).toBe(false);
    expect(store.isGhostUser).toBe(true);
    expect(store.isActiveUser).toBe(false);

    store.logout();
    expect(store.isAuthenticated).toBe(false);
    expect(store.userRole).toBeNull();
    store.setProfileForTesting(null);
    expect(store.lastUpdatedAt).toBeNull();
  });

  it('propaga errores de login, registro y fetchProfile sin sesión previa ni instancia ApiError', async () => {
    const store = useAuthStore();
    // fetchProfile con error genérico cuando data es null
    vi.spyOn(apiClient, 'apiRequest').mockRejectedValueOnce(new Error('Fallo genérico'));
    const resNull = await store.fetchProfile();
    expect(resNull).toBeNull();
    expect(store.isStale).toBe(false);

    vi.spyOn(apiClient, 'apiRequest').mockRejectedValueOnce(new Error('Login no-ApiError'));
    await expect(store.login('mal@test.com', 'bad')).rejects.toThrow('Error al iniciar sesión');

    vi.spyOn(apiClient, 'apiRequest').mockRejectedValueOnce(new Error('Reg no-ApiError'));
    await expect(
      store.register(
        {
          nombre: 'X',
          cedula: 'V-1',
          correo: 'mal@test.com',
          telefono: '0414',
          password: 'Password123!',
          unidad_solicitada_id: 1,
          tipo_ocupante_solicitado: 'PROPIETARIO',
        },
        'key-2',
      ),
    ).rejects.toThrow('Error en el registro');
  });
});
