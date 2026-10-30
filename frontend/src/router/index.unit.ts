import { beforeEach, describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { buildAppRouter, evaluateNavigationGuard } from './index';
import { useAuthStore } from '../stores/authStore';

describe('Guardias de Navegación Vue Router (router/index.ts)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('evalúa rutas públicas, de contención fantasma (/espera-aprobacion) y protegidas por RBAC', () => {
    // 1. No autenticado
    const unauth = {
      isAuthenticated: false,
      isGhostUser: false,
      isActiveUser: false,
      userRole: null,
    };
    expect(evaluateNavigationGuard({ meta: { public: true } }, unauth)).toBe(true);
    expect(evaluateNavigationGuard({ meta: { ghostOnly: true } }, unauth)).toBe('/login');
    expect(evaluateNavigationGuard({ meta: { requiresActive: true } }, unauth)).toBe('/login');

    // 2. Usuario Fantasma autenticado -> confinado a /espera-aprobacion
    const ghost = {
      isAuthenticated: true,
      isGhostUser: true,
      isActiveUser: false,
      userRole: 'FANTASMA' as const,
    };
    expect(evaluateNavigationGuard({ meta: { public: true } }, ghost)).toBe('/espera-aprobacion');
    expect(evaluateNavigationGuard({ meta: { ghostOnly: true } }, ghost)).toBe(true);
    expect(evaluateNavigationGuard({ meta: { requiresActive: true } }, ghost)).toBe(
      '/espera-aprobacion',
    );

    // 3. Usuario Activo PROPIETARIO -> entra a /dashboard pero no a /admin/usuarios
    const activeProp = {
      isAuthenticated: true,
      isGhostUser: false,
      isActiveUser: true,
      userRole: 'PROPIETARIO' as const,
    };
    expect(evaluateNavigationGuard({ meta: { public: true } }, activeProp)).toBe('/dashboard');
    expect(evaluateNavigationGuard({ meta: { ghostOnly: true } }, activeProp)).toBe('/dashboard');
    expect(evaluateNavigationGuard({ meta: { requiresActive: true } }, activeProp)).toBe(true);
    expect(
      evaluateNavigationGuard(
        { meta: { requiresActive: true, roles: ['PRESIDENTE'] } },
        activeProp,
      ),
    ).toBe('/dashboard');

    // 4. Usuario Activo PRESIDENTE -> entra a ruta restringida
    const activePres = {
      isAuthenticated: true,
      isGhostUser: false,
      isActiveUser: true,
      userRole: 'PRESIDENTE' as const,
    };
    expect(
      evaluateNavigationGuard(
        { meta: { requiresActive: true, roles: ['PRESIDENTE'] } },
        activePres,
      ),
    ).toBe(true);
  });

  it('integra el guardia en una instancia real de Vue Router con Pinia', async () => {
    const authStore = useAuthStore();
    const router = buildAppRouter(true);

    await router.push('/dashboard');
    expect(router.currentRoute.value.path).toBe('/login');

    authStore.setProfileForTesting({
      id: 9,
      nombre: 'Fantasma',
      cedula: 'V-9',
      correo: 'f@test.com',
      telefono: '0414',
      es_activo: false,
      rol: 'FANTASMA',
    });
    await router.push('/dashboard');
    expect(router.currentRoute.value.path).toBe('/espera-aprobacion');
  });
});
