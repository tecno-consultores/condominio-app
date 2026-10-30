import {
  createMemoryHistory,
  createRouter,
  createWebHistory,
  type RouteLocationNormalizedLoaded,
  type Router,
  type RouteRecordRaw,
} from 'vue-router';
import { useAuthStore, type RolUsuario } from '../stores/authStore';
import LoginView from '../views/auth/LoginView.vue';
import PendingApprovalView from '../views/auth/PendingApprovalView.vue';
import RegisterView from '../views/auth/RegisterView.vue';
import DashboardView from '../views/finance/DashboardView.vue';

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { public: true },
  },
  {
    path: '/register',
    name: 'register',
    component: RegisterView,
    meta: { public: true },
  },
  {
    path: '/espera-aprobacion',
    name: 'espera-aprobacion',
    component: PendingApprovalView,
    meta: { ghostOnly: true },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardView,
    meta: { requiresActive: true },
  },
  {
    path: '/admin/usuarios',
    name: 'admin-usuarios',
    component: DashboardView,
    meta: { requiresActive: true, roles: ['PRESIDENTE', 'VICEPRESIDENTE'] as RolUsuario[] },
  },
];

export interface AuthGuardState {
  isAuthenticated: boolean;
  isGhostUser: boolean;
  isActiveUser: boolean;
  userRole: RolUsuario | null;
}

export function evaluateNavigationGuard(
  to: Pick<RouteLocationNormalizedLoaded, 'meta'>,
  auth: AuthGuardState,
): true | string {
  const isPublic = Boolean(to.meta?.public);
  const isGhostOnly = Boolean(to.meta?.ghostOnly);
  const allowedRoles = to.meta?.roles as RolUsuario[] | undefined;

  if (isPublic) {
    if (auth.isGhostUser) {
      return '/espera-aprobacion';
    }
    if (auth.isActiveUser) {
      return '/dashboard';
    }
    return true;
  }

  if (isGhostOnly) {
    if (!auth.isAuthenticated) {
      return '/login';
    }
    if (auth.isActiveUser) {
      return '/dashboard';
    }
    return true;
  }

  if (!auth.isAuthenticated) {
    return '/login';
  }
  if (auth.isGhostUser) {
    return '/espera-aprobacion';
  }
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

  router.beforeEach((to) => {
    const authStore = useAuthStore();
    return evaluateNavigationGuard(to, {
      isAuthenticated: authStore.isAuthenticated,
      isGhostUser: authStore.isGhostUser,
      isActiveUser: authStore.isActiveUser,
      userRole: authStore.userRole,
    });
  });

  return router;
}
