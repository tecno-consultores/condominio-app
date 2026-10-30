import {
  createMemoryHistory,
  createRouter,
  createWebHistory,
  type RouteLocationNormalizedLoaded,
  type Router,
  type RouteRecordRaw,
} from 'vue-router';
import { useAuthStore, type RolUsuario } from '../stores/authStore';
import AdminBoardRolesView from '../views/admin/AdminBoardRolesView.vue';
import AdminGhostUsersView from '../views/admin/AdminGhostUsersView.vue';
import AdminStructureView from '../views/admin/AdminStructureView.vue';
import LoginView from '../views/auth/LoginView.vue';
import PendingApprovalView from '../views/auth/PendingApprovalView.vue';
import RegisterView from '../views/auth/RegisterView.vue';
import BillingGeneratorView from '../views/finance/BillingGeneratorView.vue';
import DashboardView from '../views/finance/DashboardView.vue';
import PaymentWizardView from '../views/finance/PaymentWizardView.vue';
import SolvencyCertificateView from '../views/finance/SolvencyCertificateView.vue';
import TreasuryClosingView from '../views/finance/TreasuryClosingView.vue';
import TreasuryPaymentsView from '../views/finance/TreasuryPaymentsView.vue';
import ConsultationDetailView from '../views/governance/ConsultationDetailView.vue';
import ConsultationsListView from '../views/governance/ConsultationsListView.vue';
import GatehouseScannerView from '../views/operations/GatehouseScannerView.vue';
import AmenitiesReservationView from '../views/operations/AmenitiesReservationView.vue';
import IncidentsFeedView from '../views/operations/IncidentsFeedView.vue';
import OperationsTasksView from '../views/operations/OperationsTasksView.vue';
import ParcelsTrackerView from '../views/operations/ParcelsTrackerView.vue';
import SecretaryLogbookView from '../views/operations/SecretaryLogbookView.vue';
import SpokespersonGalleryView from '../views/operations/SpokespersonGalleryView.vue';
import VisitorPassesView from '../views/operations/VisitorPassesView.vue';

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
    alias: ['/inicio'],
    name: 'dashboard',
    component: DashboardView,
    meta: { requiresActive: true },
  },
  {
    path: '/finanzas/reportar-pago',
    alias: ['/pagar'],
    name: 'reportar-pago',
    component: PaymentWizardView,
    meta: { requiresActive: true },
  },
  {
    path: '/tesoreria/pagos',
    alias: ['/admin/pagos-revision'],
    name: 'tesoreria-pagos',
    component: TreasuryPaymentsView,
    meta: { requiresActive: true, roles: ['TESORERO', 'PRESIDENTE'] as RolUsuario[] },
  },
  {
    path: '/tesoreria/cierre',
    alias: ['/admin/finanzas'],
    name: 'tesoreria-cierre',
    component: TreasuryClosingView,
    meta: { requiresActive: true, roles: ['TESORERO', 'PRESIDENTE'] as RolUsuario[] },
  },
  {
    path: '/tesoreria/facturacion',
    name: 'tesoreria-facturacion',
    component: BillingGeneratorView,
    meta: { requiresActive: true, roles: ['TESORERO', 'PRESIDENTE'] as RolUsuario[] },
  },
  {
    path: '/finanzas/solvencia',
    name: 'finanzas-solvencia',
    component: SolvencyCertificateView,
    meta: { requiresActive: true },
  },
  {
    path: '/incidencias',
    name: 'incidencias',
    component: IncidentsFeedView,
    meta: { requiresActive: true },
  },
  {
    path: '/operaciones/tareas',
    alias: ['/conserje/tareas'],
    name: 'operaciones-tareas',
    component: OperationsTasksView,
    meta: { requiresActive: true },
  },
  {
    path: '/voceros/galeria',
    name: 'voceros-galeria',
    component: SpokespersonGalleryView,
    meta: { requiresActive: true },
  },
  {
    path: '/secretaria/bitacora',
    name: 'secretaria-bitacora',
    component: SecretaryLogbookView,
    meta: { requiresActive: true },
  },
  {
    path: '/consultas',
    name: 'consultas-list',
    component: ConsultationsListView,
    meta: { requiresActive: true },
  },
  {
    path: '/consultas/:id',
    name: 'consulta-detail',
    component: ConsultationDetailView,
    meta: { requiresActive: true },
  },
  {
    path: '/accesos/pases',
    name: 'accesos-pases',
    component: VisitorPassesView,
    meta: { requiresActive: true },
  },
  {
    path: '/operaciones/garita-qr',
    name: 'operaciones-garita-qr',
    component: GatehouseScannerView,
    meta: {
      requiresActive: true,
      roles: ['CONSERJE', 'PRESIDENTE', 'VOCERO'] as RolUsuario[],
    },
  },
  {
    path: '/operaciones/paqueteria',
    name: 'operaciones-paqueteria',
    component: ParcelsTrackerView,
    meta: { requiresActive: true },
  },
  {
    path: '/reservas/areas',
    name: 'reservas-areas',
    component: AmenitiesReservationView,
    meta: { requiresActive: true },
  },
  {
    path: '/admin/estructura',
    name: 'admin-estructura',
    component: AdminStructureView,
    meta: { requiresActive: true, roles: ['PRESIDENTE', 'VICEPRESIDENTE'] as RolUsuario[] },
  },
  {
    path: '/admin/usuarios',
    alias: ['/admin/usuarios-pendientes'],
    name: 'admin-usuarios',
    component: AdminGhostUsersView,
    meta: { requiresActive: true, roles: ['PRESIDENTE', 'VICEPRESIDENTE'] as RolUsuario[] },
  },
  {
    path: '/admin/junta',
    name: 'admin-junta',
    component: AdminBoardRolesView,
    meta: { requiresActive: true, roles: ['PRESIDENTE'] as RolUsuario[] },
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
