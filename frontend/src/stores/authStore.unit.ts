import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useAuthStore, type UsuarioPerfil } from './authStore';
import { useFinanceStore } from './financeStore';
import { useOperationsStore } from './operationsStore';
import { useGovernanceStore } from './governanceStore';
import { useAccessAmenitiesStore } from './accessAmenitiesStore';
import * as apiClient from '../services/apiClient';

const PERFIL_ACTIVO: UsuarioPerfil = {
  id: 1,
  nombre: 'Carlos Pérez',
  cedula: 'V-12345678',
  correo: 'carlos@condominio.test',
  telefono: '+584141234567',
  es_activo: true,
  rol: 'PROPIETARIO',
  unidad_activa_id: 7,
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

describe('Store useAuthStore (Aislamiento SPA 11X, No Destructivo & Trimodal)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    apiClient.resetCsrfToken();
    vi.restoreAllMocks();
  });

  it('inicia sesión, carga el perfil activo y calcula activeUnitId y getters correctamente', async () => {
    const spy = vi
      .spyOn(apiClient, 'apiRequest')
      .mockResolvedValueOnce({ message: 'Login exitoso', rol: 'PROPIETARIO', csrf_token: 'c-1' })
      .mockResolvedValueOnce(PERFIL_ACTIVO);

    const store = useAuthStore();
    const res = await store.login('carlos@condominio.test', 'Password123!');

    expect(res).toEqual(PERFIL_ACTIVO);
    expect(store.isAuthenticated).toBe(true);
    expect(store.isActiveUser).toBe(true);
    expect(store.isGhostUser).toBe(false);
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(store.sessionHydrated).toBe(true);
    expect(store.userRole).toBe('PROPIETARIO');
    expect(store.activeUnitId).toBe(7);
    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy).toHaveBeenNthCalledWith(1, '/api/auth/login', {
      method: 'POST',
      body: { correo: 'carlos@condominio.test', password: 'Password123!' },
    });
    expect(spy).toHaveBeenNthCalledWith(2, '/api/auth/me');
  });

  it('preserva datos ante micro-corte de red y limpia sesión silenciosamente si /me no retorna perfil o retorna 401', async () => {
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

    // En respuesta HTML fallback de nginx.qa.conf (null), limpia sin marcar error visible
    vi.spyOn(apiClient, 'apiRequest').mockResolvedValueOnce(null as unknown as UsuarioPerfil);
    expect(await store.fetchProfile()).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(store.errorMessage).toBeNull();

    // Un 401 explícito limpia sesión sin mostrar error visible en carga inicial
    store.setProfileForTesting(PERFIL_ACTIVO);
    vi.spyOn(apiClient, 'apiRequest').mockRejectedValueOnce(
      new apiClient.ApiError(401, 'Token expirado'),
    );
    const res401 = await store.fetchProfile();
    expect(res401).toBeNull();
    expect(store.data).toBeNull();
    expect(store.isStale).toBe(false);
    expect(store.errorMessage).toBeNull();
  });

  it('envía POST /api/auth/logout antes de limpiar CSRF y resetea los 5 stores Pinia en logout y 401', async () => {
    const authStore = useAuthStore();
    const financeStore = useFinanceStore();
    const opsStore = useOperationsStore();
    const govStore = useGovernanceStore();
    const accStore = useAccessAmenitiesStore();

    authStore.setProfileForTesting(PERFIL_ACTIVO);
    authStore.setRbacNotice('Aviso previo');
    apiClient.setCsrfToken('csrf-usuario-anterior');
    financeStore.data.pagosEnRevision = [
      {
        id: 1,
        recibo_id: 2,
        usuario_id: 1,
        monto: '10.00',
        moneda: 'USD',
        monto_usd: '10.00',
        tasa_cambio: '36.50',
        metodo_pago: 'ZELLE',
        numero_referencia: 'REF',
        url_comprobante: null,
        estado: 'EN_REVISION',
      },
    ];
    opsStore.data.unidades = [{ id: 1, identificador: 'A-1', estructura_id: 1 }];
    govStore.consultas = [{ id: 5 } as unknown as (typeof govStore.consultas)[0]];
    accStore.pases = [{ id: 8 } as unknown as (typeof accStore.pases)[0]];

    let csrfSeenByLogout = '';
    vi.spyOn(apiClient, 'apiRequest').mockImplementationOnce(async () => {
      csrfSeenByLogout = apiClient.getCsrfToken();
      return { message: 'ok' };
    });

    await authStore.logout();

    expect(csrfSeenByLogout).toBe('csrf-usuario-anterior');
    expect(apiClient.getCsrfToken()).toBe('csrf-client-initialized');
    expect(authStore.isAuthenticated).toBe(false);
    expect(authStore.rbacNotice).toBeNull();
    expect(financeStore.data.pagosEnRevision).toEqual([]);
    expect(financeStore.data.resumen).toBeNull();
    expect(opsStore.data.unidades).toEqual([]);
    expect(govStore.consultas).toEqual([]);
    expect(accStore.pases).toEqual([]);
  });

  it('registra un Usuario Fantasma con Idempotency-Key y evalúa fronteras mixtas', async () => {
    const regSpy = vi.spyOn(apiClient, 'apiRequest').mockResolvedValueOnce(PERFIL_FANTASMA);
    const store = useAuthStore();

    const payloadRegistro = {
      nombre: 'Nuevo Vecino',
      cedula: 'V-99999999',
      correo: 'fantasma@condominio.test',
      telefono: '+584149999999',
      password: 'Password123!',
      unidad_solicitada_id: 1,
      tipo_ocupante_solicitado: 'PROPIETARIO' as const,
    };
    const created = await store.register(payloadRegistro, 'idem-reg-001');

    expect(regSpy).toHaveBeenCalledWith('/api/auth/register', {
      method: 'POST',
      idempotencyKey: 'idem-reg-001',
      body: payloadRegistro,
    });
    expect(created.es_activo).toBe(false);
    expect(store.isGhostUser).toBe(true);
    expect(store.isActiveUser).toBe(false);
    expect(store.activeUnitId).toBeNull();

    store.setProfileForTesting({ ...PERFIL_ACTIVO, rol: 'FANTASMA' });
    expect(store.isGhostUser).toBe(true);
    expect(store.isActiveUser).toBe(false);
    store.setProfileForTesting({ ...PERFIL_ACTIVO, es_activo: false });
    expect(store.isGhostUser).toBe(true);
    expect(store.isActiveUser).toBe(false);

    vi.spyOn(apiClient, 'apiRequest').mockResolvedValueOnce({ message: 'ok' });
    await store.logout();
    expect(store.isAuthenticated).toBe(false);
    expect(store.userRole).toBeNull();
    store.setProfileForTesting(null);
    expect(store.lastUpdatedAt).toBeNull();
  });

  it('propaga errores de login, registro y fetchProfile sin sesión previa ni instancia ApiError', async () => {
    const store = useAuthStore();
    vi.spyOn(apiClient, 'apiRequest').mockRejectedValueOnce(new Error('Fallo genérico'));
    const resNull = await store.fetchProfile();
    expect(resNull).toBeNull();
    expect(store.isStale).toBe(false);
    expect(store.errorMessage).toBe('Error inesperado');

    store.setProfileForTesting(PERFIL_ACTIVO);
    vi.spyOn(apiClient, 'apiRequest').mockRejectedValueOnce(new apiClient.ApiError(503, 'Caído'));
    await store.fetchProfile();
    expect(store.isStale).toBe(true);
    vi.spyOn(apiClient, 'apiRequest').mockResolvedValueOnce(PERFIL_ACTIVO);
    await store.fetchProfile();
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

  it('maneja 401 con redirect seguro y evita bucle en /login y /register', async () => {
    const mockPush = vi.fn().mockResolvedValue(undefined);
    const { registerAuthRouter } = await import('./authStore');
    const mockRouter = {
      currentRoute: { value: { path: '/dashboard', fullPath: '/dashboard' } },
      push: mockPush,
    } as unknown as Parameters<typeof registerAuthRouter>[0];
    registerAuthRouter(mockRouter);

    const store = useAuthStore();
    store.setProfileForTesting(PERFIL_ACTIVO);
    await store.handleUnauthorizedError(new apiClient.ApiError(401, 'Expirada'));
    expect(store.isAuthenticated).toBe(false);
    expect(store.errorMessage).toBe('Su sesión ha expirado. Inicie sesión nuevamente.');
    expect(mockPush).toHaveBeenCalledWith('/login');

    // En ruta secundaria protegida preserva ?redirect=
    mockPush.mockClear();
    store.setProfileForTesting(PERFIL_ACTIVO);
    (mockRouter.currentRoute as { value: { path: string; fullPath: string } }).value = {
      path: '/consultas/4',
      fullPath: '/consultas/4?tab=voto',
    };
    await store.handleUnauthorizedError(new apiClient.ApiError(401, 'Expirada'));
    expect(mockPush).toHaveBeenCalledWith({
      path: '/login',
      query: { redirect: '/consultas/4?tab=voto' },
    });

    // No navega si ya está en /login o /register
    store.setProfileForTesting(PERFIL_ACTIVO);
    mockPush.mockClear();
    (mockRouter.currentRoute as { value: { path: string; fullPath: string } }).value = {
      path: '/login',
      fullPath: '/login',
    };
    expect(await store.handleUnauthorizedError(new apiClient.ApiError(401, 'Expirada'))).toBe(true);
    expect(mockPush).not.toHaveBeenCalled();

    store.setProfileForTesting(PERFIL_ACTIVO);
    (mockRouter.currentRoute as { value: { path: string; fullPath: string } }).value = {
      path: '/register',
      fullPath: '/register',
    };
    expect(await store.handleUnauthorizedError(new apiClient.ApiError(401, 'Expirada'))).toBe(true);
    expect(mockPush).not.toHaveBeenCalled();

    // Error no-401 retorna false sin limpiar sesión
    store.setProfileForTesting(PERFIL_ACTIVO);
    expect(await store.handleUnauthorizedError(new apiClient.ApiError(500, 'Server'))).toBe(false);
    expect(store.isAuthenticated).toBe(true);

    // Si /api/auth/logout falla en red, limpia la sesión local en finally
    vi.spyOn(apiClient, 'apiRequest').mockRejectedValueOnce(new Error('Offline'));
    await store.logout();
    expect(store.isAuthenticated).toBe(false);
  });

  it('invoca el callback de sesión 401 desde apiClient con y sin sesión activa en memoria', async () => {
    const store = useAuthStore();
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    // Sin perfil activo -> clearSession()
    store.setProfileForTesting(null);
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'No autenticado' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    await expect(apiClient.apiRequest('/api/operaciones/incidencias')).rejects.toThrow();
    expect(store.isAuthenticated).toBe(false);

    // Con perfil activo -> handleUnauthorizedError()
    store.setProfileForTesting(PERFIL_ACTIVO);
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Token revocado' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    await expect(apiClient.apiRequest('/api/operaciones/incidencias')).rejects.toThrow();
    expect(store.isAuthenticated).toBe(false);
  });
});
