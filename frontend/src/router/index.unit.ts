import { beforeEach, describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { buildAppRouter, evaluateNavigationGuard } from './index';
import { useAuthStore } from '../stores/authStore';

describe('Guardias de Navegación Vue Router (router/index.ts)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('evalúa rutas públicas, de contención fantasma (/espera-aprobacion) y protegidas por RBAC', () => {
    const unauth = {
      isAuthenticated: false,
      isGhostUser: false,
      isActiveUser: false,
      userRole: null,
    };
    expect(evaluateNavigationGuard({ meta: { public: true } }, unauth)).toBe(true);
    expect(evaluateNavigationGuard({ meta: { ghostOnly: true } }, unauth)).toBe('/login');
    expect(evaluateNavigationGuard({ meta: { requiresActive: true } }, unauth)).toBe('/login');

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
        { meta: { requiresActive: true, roles: ['TESORERO', 'PRESIDENTE'] } },
        activeProp,
      ),
    ).toBe('/dashboard');

    const activeTes = {
      isAuthenticated: true,
      isGhostUser: false,
      isActiveUser: true,
      userRole: 'TESORERO' as const,
    };
    expect(
      evaluateNavigationGuard(
        { meta: { requiresActive: true, roles: ['TESORERO', 'PRESIDENTE'] } },
        activeTes,
      ),
    ).toBe(true);
  });

  it('integra el guardia en una instancia real de Vue Router con Pinia y rutas de Hito 6', async () => {
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
    await router.push('/finanzas/reportar-pago');
    expect(router.currentRoute.value.path).toBe('/espera-aprobacion');

    authStore.setProfileForTesting({
      id: 10,
      nombre: 'Tesorero',
      cedula: 'V-10',
      correo: 'tesorero@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'TESORERO',
    });
    await router.push('/tesoreria/pagos');
    expect(router.currentRoute.value.path).toBe('/tesoreria/pagos');
    await router.push('/tesoreria/cierre');
    expect(router.currentRoute.value.path).toBe('/tesoreria/cierre');
  });
});
