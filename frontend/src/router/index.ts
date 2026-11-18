import {
  createMemoryHistory,
  createRouter,
  createWebHistory,
  type RouteLocationNormalizedLoaded,
  type Router,
  type RouteRecordRaw,
} from 'vue-router';
import { registerAuthRouter, useAuthStore, type RolUsuario } from '../stores/authStore';
import {
  getActiveConsultationTransition,
  setActiveConsultationTransition,
} from '../composables/useViewTransition';
import { isSafeRedirectUrl } from '../utils/security';
import AppShellLayout from '../components/layout/AppShellLayout.vue';

export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/auth/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../views/auth/RegisterView.vue'),
    meta: { public: true },
  },
  {
    path: '/espera-aprobacion',
    name: 'espera-aprobacion',
    component: () => import('../views/auth/PendingApprovalView.vue'),
    meta: { ghostOnly: true },
  },
  {
    path: '/',
    component: AppShellLayout,
    children: [
      {
        path: '',
        redirect: '/dashboard',
      },
      {
        path: 'dashboard',
        alias: ['/inicio'],
        name: 'dashboard',
        component: () => import('../views/finance/DashboardView.vue'),
        meta: { requiresActive: true },
      },
      {
        path: 'finanzas/reportar-pago',
        alias: ['/pagar'],
        name: 'reportar-pago',
        component: () => import('../views/finance/PaymentWizardView.vue'),
        meta: { requiresActive: true },
      },
      {
        path: 'tesoreria/pagos',
        alias: ['/admin/pagos-revision'],
        name: 'tesoreria-pagos',
        component: () => import('../views/finance/TreasuryPaymentsView.vue'),
        meta: { requiresActive: true, roles: ['TESORERO', 'PRESIDENTE'] as RolUsuario[] },
      },
      {
        path: 'tesoreria/cierre',
        alias: ['/admin/finanzas'],
        name: 'tesoreria-cierre',
        component: () => import('../views/finance/TreasuryClosingView.vue'),
        meta: { requiresActive: true, roles: ['TESORERO', 'PRESIDENTE'] as RolUsuario[] },
      },
      {
        path: 'tesoreria/facturacion',
        name: 'tesoreria-facturacion',
        component: () => import('../views/finance/BillingGeneratorView.vue'),
        meta: { requiresActive: true, roles: ['TESORERO', 'PRESIDENTE'] as RolUsuario[] },
      },
      {
        path: 'finanzas/solvencia',
        name: 'finanzas-solvencia',
        component: () => import('../views/finance/SolvencyCertificateView.vue'),
        meta: { requiresActive: true },
      },
      {
        path: 'incidencias',
        name: 'incidencias',
        component: () => import('../views/operations/IncidentsFeedView.vue'),
        meta: { requiresActive: true },
      },
      {
        path: 'operaciones/tareas',
        alias: ['/conserje/tareas'],
        name: 'operaciones-tareas',
        component: () => import('../views/operations/OperationsTasksView.vue'),
        meta: { requiresActive: true },
      },
      {
        path: 'voceros/galeria',
        name: 'voceros-galeria',
        component: () => import('../views/operations/SpokespersonGalleryView.vue'),
        meta: { requiresActive: true },
      },
      {
        path: 'secretaria/bitacora',
        name: 'secretaria-bitacora',
        component: () => import('../views/operations/SecretaryLogbookView.vue'),
        meta: { requiresActive: true },
      },
      {
        path: 'consultas',
        name: 'consultas-list',
        component: () => import('../views/governance/ConsultationsListView.vue'),
        meta: { requiresActive: true },
      },
      {
        path: 'consultas/:id',
        name: 'consulta-detail',
        component: () => import('../views/governance/ConsultationDetailView.vue'),
        meta: { requiresActive: true },
      },
      {
        path: 'accesos/pases',
        name: 'accesos-pases',
        component: () => import('../views/operations/VisitorPassesView.vue'),
        meta: { requiresActive: true },
      },
      {
        path: 'operaciones/garita-qr',
        name: 'operaciones-garita-qr',
        component: () => import('../views/operations/GatehouseScannerView.vue'),
        meta: {
          requiresActive: true,
          roles: ['CONSERJE', 'PRESIDENTE', 'VOCERO'] as RolUsuario[],
        },
      },
      {
        path: 'operaciones/paqueteria',
        name: 'operaciones-paqueteria',
        component: () => import('../views/operations/ParcelsTrackerView.vue'),
        meta: { requiresActive: true },
      },
      {
        path: 'reservas/areas',
        name: 'reservas-areas',
        component: () => import('../views/operations/AmenitiesReservationView.vue'),
        meta: { requiresActive: true },
      },
      {
        path: 'admin/estructura',
        name: 'admin-estructura',
        component: () => import('../views/admin/AdminStructureView.vue'),
        meta: { requiresActive: true, roles: ['PRESIDENTE', 'VICEPRESIDENTE'] as RolUsuario[] },
      },
      {
        path: 'admin/usuarios',
        alias: ['/admin/usuarios-pendientes'],
        name: 'admin-usuarios',
        component: () => import('../views/admin/AdminGhostUsersView.vue'),
        meta: { requiresActive: true, roles: ['PRESIDENTE', 'VICEPRESIDENTE'] as RolUsuario[] },
      },
      {
        path: 'admin/junta',
        name: 'admin-junta',
        component: () => import('../views/admin/AdminBoardRolesView.vue'),
        meta: { requiresActive: true, roles: ['PRESIDENTE'] as RolUsuario[] },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/auth/NotFoundView.vue'),
    meta: { publicNotFound: true },
  },
];

export interface AuthGuardState {
  isAuthenticated: boolean;
  isGhostUser: boolean;
  isActiveUser: boolean;
  userRole: RolUsuario | null;
}

export type GuardRouteTarget = Pick<RouteLocationNormalizedLoaded, 'meta'> & {
  path?: string;
  fullPath?: string;
  query?: Record<string, unknown>;
};

function resolvePublicRedirect(to: GuardRouteTarget, auth: AuthGuardState): true | string {
  if (auth.isGhostUser) {
    return '/espera-aprobacion';
  }
  if (!auth.isActiveUser) {
    return true;
  }
  const rawRedirect = typeof to.query?.redirect === 'string' ? to.query.redirect : null;
  if (
    rawRedirect &&
    isSafeRedirectUrl(rawRedirect) &&
    !rawRedirect.startsWith('/login') &&
    !rawRedirect.startsWith('/register') &&
    !rawRedirect.startsWith('/espera-aprobacion')
  ) {
    return rawRedirect;
  }
  return '/dashboard';
}

function resolveGhostRedirect(auth: AuthGuardState): true | string {
  if (!auth.isAuthenticated) {
    return '/login';
  }
  return auth.isActiveUser ? '/dashboard' : true;
}

function buildLoginRedirectTarget(to: GuardRouteTarget): string {
  const fullPath = to.fullPath;
  if (
    fullPath &&
    to.path !== '/dashboard' &&
    isSafeRedirectUrl(fullPath) &&
    !fullPath.startsWith('/login')
  ) {
    return `/login?redirect=${encodeURIComponent(fullPath)}`;
  }
  return '/login';
}

export function evaluateNavigationGuard(to: GuardRouteTarget, auth: AuthGuardState): true | string {
  if (to.meta?.publicNotFound) {
    return true;
  }
  if (to.meta?.public) {
    return resolvePublicRedirect(to, auth);
  }
  if (to.meta?.ghostOnly) {
    return resolveGhostRedirect(auth);
  }
  if (!auth.isAuthenticated) {
    return buildLoginRedirectTarget(to);
  }
  if (auth.isGhostUser) {
    return '/espera-aprobacion';
  }
  const allowedRoles = to.meta?.roles as RolUsuario[] | undefined;
  if (allowedRoles && (!auth.userRole || !allowedRoles.includes(auth.userRole))) {
    return '/dashboard';
  }
  return true;
}

export function buildAppRouter(useMemory = false): Router {
  const router = createRouter({
    history: useMemory ? createMemoryHistory() : createWebHistory(),
    routes,
  });

  registerAuthRouter(router);

  router.beforeEach(async (to) => {
    const authStore = useAuthStore();
    if (!authStore.sessionHydrated && !to.meta?.publicNotFound) {
      await authStore.fetchProfile();
    }

    const decision = evaluateNavigationGuard(to, {
      isAuthenticated: authStore.isAuthenticated,
      isGhostUser: authStore.isGhostUser,
      isActiveUser: authStore.isActiveUser,
      userRole: authStore.userRole,
    });

    const allowedRoles = to.meta?.roles as RolUsuario[] | undefined;
    if (
      decision === '/dashboard' &&
      Array.isArray(allowedRoles) &&
      (!authStore.userRole || !allowedRoles.includes(authStore.userRole))
    ) {
      authStore.setRbacNotice('No posee permisos para acceder a la sección solicitada.');
    }

    return decision;
  });

  router.afterEach(() => {
    if (getActiveConsultationTransition() !== null) {
      queueMicrotask(() => setActiveConsultationTransition(null));
    }
    if (typeof document !== 'undefined' && document.activeElement === document.body) {
      const target = document.querySelector<HTMLElement>('#app-main-content, main, h1');
      if (target) {
        if (!target.hasAttribute('tabindex')) {
          target.setAttribute('tabindex', '-1');
        }
        if (typeof target.focus === 'function') {
          target.focus({ preventScroll: true });
        }
      }
    }
  });

  return router;
}
