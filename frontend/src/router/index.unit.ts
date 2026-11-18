import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { buildAppRouter, evaluateNavigationGuard } from './index';
import {
  getActiveConsultationTransition,
  setActiveConsultationTransition,
} from '../composables/useViewTransition';
import * as apiClient from '../services/apiClient';
import { useAuthStore } from '../stores/authStore';

describe('Guardias de Navegación Vue Router (router/index.ts)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
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
    expect(
      evaluateNavigationGuard(
        { meta: { requiresActive: true }, path: '/consultas', fullPath: '/consultas?page=2' },
        unauth,
      ),
    ).toBe('/login?redirect=%2Fconsultas%3Fpage%3D2');
    expect(evaluateNavigationGuard({ meta: { publicNotFound: true } }, unauth)).toBe(true);

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
    expect(
      evaluateNavigationGuard(
        { meta: { public: true }, query: { redirect: '/consultas/5' } },
        activeProp,
      ),
    ).toBe('/consultas/5');
    expect(
      evaluateNavigationGuard(
        { meta: { public: true }, query: { redirect: '/\t/evil.com' } },
        activeProp,
      ),
    ).toBe('/dashboard');
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

  it('integra el guardia en una instancia real de Vue Router con Pinia y rutas de Hito 6 y Hito 7', async () => {
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
    await router.push('/tesoreria/facturacion');
    expect(router.currentRoute.value.path).toBe('/tesoreria/facturacion');
    await router.push('/finanzas/solvencia');
    expect(router.currentRoute.value.path).toBe('/finanzas/solvencia');
    await router.push('/tesoreria/cierre');
    expect(router.currentRoute.value.path).toBe('/tesoreria/cierre');
    await router.push('/incidencias');
    expect(router.currentRoute.value.path).toBe('/incidencias');
    await router.push('/operaciones/tareas');
    expect(router.currentRoute.value.path).toBe('/operaciones/tareas');
    await router.push('/voceros/galeria');
    expect(router.currentRoute.value.path).toBe('/voceros/galeria');
    await router.push('/secretaria/bitacora');
    expect(router.currentRoute.value.path).toBe('/secretaria/bitacora');

    // Tesorero intentando entrar a ruta exclusiva de Presidencia redirige a /dashboard
    await router.push('/admin/junta');
    expect(router.currentRoute.value.path).toBe('/dashboard');

    authStore.setProfileForTesting({
      id: 1,
      nombre: 'Presidente',
      cedula: 'V-1',
      correo: 'presidente@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PRESIDENTE',
    });
    await router.push('/admin/estructura');
    expect(router.currentRoute.value.path).toBe('/admin/estructura');
    await router.push('/admin/usuarios');
    expect(router.currentRoute.value.path).toBe('/admin/usuarios');
    await router.push('/admin/junta');
    expect(router.currentRoute.value.path).toBe('/admin/junta');
  });

  it('hidrata sesión vía /api/auth/me en carga inicial y fija rbacNotice al denegar rol (Hito 17.2)', async () => {
    const authStore = useAuthStore();
    expect(authStore.sessionHydrated).toBe(false);

    const fetchSpy = vi.spyOn(apiClient, 'apiRequest').mockResolvedValueOnce({
      id: 21,
      nombre: 'Residente Hidratado',
      cedula: 'V-21',
      correo: 'h@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
      unidad_activa_id: 7,
    });

    const router = buildAppRouter(true);
    await router.push('/admin/junta');
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(authStore.sessionHydrated).toBe(true);
    expect(router.currentRoute.value.path).toBe('/dashboard');
    expect(authStore.rbacNotice).toContain('No posee permisos');

    // Segunda navegación no vuelve a invocar fetchProfile innecesariamente
    const mainEl = document.createElement('main');
    mainEl.id = 'app-main-content';
    const focusSpy = vi.spyOn(mainEl, 'focus');
    document.body.appendChild(mainEl);
    setActiveConsultationTransition(99);

    await router.push('/incidencias');
    await Promise.resolve();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(router.currentRoute.value.path).toBe('/incidencias');
    expect(getActiveConsultationTransition()).toBeNull();
    expect(mainEl.getAttribute('tabindex')).toBe('-1');
    expect(focusSpy).toHaveBeenCalledWith({ preventScroll: true });
    mainEl.remove();

    // Ruta inexistente cae en NotFoundView (404)
    await router.push('/no-existe-esta-vista-404');
    expect(router.currentRoute.value.name).toBe('not-found');
  });

  it('hidrata sesión en recarga fría de /login y honra ?redirect= seguro (Hito 22.2)', async () => {
    const fetchSpy = vi.spyOn(apiClient, 'apiRequest').mockResolvedValueOnce({
      id: 22,
      nombre: 'Laura Hidratada',
      cedula: 'V-22',
      correo: 'laura@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
      unidad_activa_id: 3,
    });

    const router = buildAppRouter(true);
    await router.push('/login?redirect=%2Faccesos%2Fpases');
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(router.currentRoute.value.path).toBe('/accesos/pases');
  });

  it('carga los módulos lazy de todas las rutas y rechaza redirects inseguros', async () => {
    vi.spyOn(apiClient, 'apiRequest').mockResolvedValueOnce({
      id: 1,
      nombre: 'Admin Lazy',
      cedula: 'V-1',
      correo: 'admin@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PRESIDENTE',
      unidad_activa_id: 1,
    });

    const router = buildAppRouter(true);
    await router.push('/login?redirect=https%3A%2F%2Fevil.example.com');
    expect(router.currentRoute.value.path).toBe('/dashboard');

    // Resolver todos los loaders lazy () => import(...) para cobertura de funciones
    const lazyLoaders = router
      .getRoutes()
      .map((record) => record.components?.default)
      .filter((comp): comp is () => Promise<unknown> => typeof comp === 'function');

    await Promise.all(lazyLoaders.map((loader) => loader()));
    expect(lazyLoaders.length).toBeGreaterThanOrEqual(20);

    // Usuario ya activo navegando a /espera-aprobacion redirige al panel
    await router.push('/espera-aprobacion');
    expect(router.currentRoute.value.path).toBe('/dashboard');
  });
});
