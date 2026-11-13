<script setup lang="ts">
import { computed } from 'vue';
import { getActivePinia } from 'pinia';
import { useAuthStore, type RolUsuario } from '../../stores/authStore';

const props = defineProps<{
  userName: string;
  role: RolUsuario | null;
  currentPath: string;
}>();

const emit = defineEmits<{
  (e: 'navigate', to: string): void;
  (e: 'logout'): void;
}>();

interface SidebarLinkItem {
  id: string;
  label: string;
  to: string;
  roles?: RolUsuario[];
}

const links: SidebarLinkItem[] = [
  { id: 'side-dashboard', label: 'Resumen Financiero', to: '/dashboard' },
  { id: 'side-pagar', label: 'Reportar Pago', to: '/finanzas/reportar-pago' },
  { id: 'side-solvencia', label: 'Certificado de Solvencia', to: '/finanzas/solvencia' },
  {
    id: 'side-revision-pagos',
    label: 'Aprobación de Pagos',
    to: '/tesoreria/pagos',
    roles: ['TESORERO', 'PRESIDENTE'],
  },
  {
    id: 'side-cierre-mensual',
    label: 'Cierre Mensual Contable',
    to: '/tesoreria/cierre',
    roles: ['TESORERO', 'PRESIDENTE'],
  },
  {
    id: 'side-facturacion',
    label: 'Facturación Mensual LPH',
    to: '/tesoreria/facturacion',
    roles: ['TESORERO', 'PRESIDENTE'],
  },
  { id: 'side-incidencias', label: 'Embudo de Incidencias', to: '/incidencias' },
  { id: 'side-tareas', label: 'Tareas de Conserjería', to: '/operaciones/tareas' },
  { id: 'side-voceros', label: 'Galería de Voceros', to: '/voceros/galeria' },
  { id: 'side-bitacora', label: 'Bitácora de Actas', to: '/secretaria/bitacora' },
  { id: 'side-consultas', label: 'Cartas Consulta (Art. 23)', to: '/consultas' },
  { id: 'side-pases-qr', label: 'Pases de Visita QR', to: '/accesos/pases' },
  {
    id: 'side-garita-qr',
    label: 'Escáner Garita QR',
    to: '/operaciones/garita-qr',
    roles: ['CONSERJE', 'PRESIDENTE', 'VOCERO'],
  },
  { id: 'side-paqueteria', label: 'Paquetería en Garita', to: '/operaciones/paqueteria' },
  { id: 'side-reservas', label: 'Reserva de Áreas Sociales', to: '/reservas/areas' },
  {
    id: 'side-estructura',
    label: 'Estructura Física',
    to: '/admin/estructura',
    roles: ['PRESIDENTE', 'VICEPRESIDENTE'],
  },
  {
    id: 'side-usuarios',
    label: 'Usuarios Fantasma',
    to: '/admin/usuarios',
    roles: ['PRESIDENTE', 'VICEPRESIDENTE'],
  },
  {
    id: 'side-junta',
    label: 'Junta de Condominio',
    to: '/admin/junta',
    roles: ['PRESIDENTE'],
  },
];

const effectiveRole = computed<RolUsuario | null>(() => {
  if (props.role) {
    return props.role;
  }
  const pinia = getActivePinia();
  return pinia ? useAuthStore(pinia).userRole : null;
});

const visibleLinks = computed<SidebarLinkItem[]>(() =>
  links.filter(
    (link) =>
      !link.roles || (effectiveRole.value !== null && link.roles.includes(effectiveRole.value)),
  ),
);
</script>

<template>
  <aside id="desktop-sidebar" class="sidebar" aria-label="Menú lateral de escritorio">
    <div class="sidebar__brand">
      <strong class="sidebar__title">Condominio App</strong>
      <span class="sidebar__role-badge">{{ effectiveRole || 'RESIDENTE' }}</span>
    </div>

    <p class="sidebar__user">{{ userName }}</p>

    <ul class="sidebar__list">
      <li v-for="link in visibleLinks" :key="link.to">
        <button
          :id="link.id"
          type="button"
          class="sidebar__link"
          :class="{ 'sidebar__link--active': currentPath === link.to }"
          :aria-current="currentPath === link.to ? 'page' : undefined"
          @click="emit('navigate', link.to)"
        >
          {{ link.label }}
        </button>
      </li>
    </ul>

    <button id="btn-sidebar-logout" type="button" class="sidebar__logout" @click="emit('logout')">
      Cerrar Sesión
    </button>
  </aside>
</template>

<style scoped>
.sidebar {
  display: none;
  width: 16rem;
  flex-shrink: 0;
  background-color: #0f172a;
  color: #f8fafc;
  padding: 1.5rem 1rem;
  flex-direction: column;
  border-right: 1px solid #1e293b;
}

.sidebar__brand {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.sidebar__title {
  font-size: 1.125rem;
}

.sidebar__role-badge {
  font-size: 0.7rem;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  background-color: #1e293b;
  color: #38bdf8;
  font-weight: 700;
}

.sidebar__user {
  font-size: 0.875rem;
  color: #94a3b8;
  margin-bottom: 1.5rem;
}

.sidebar__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  flex: 1;
}

.sidebar__link {
  width: 100%;
  text-align: left;
  padding: 0.625rem 0.75rem;
  border-radius: 0.5rem;
  border: none;
  background: transparent;
  color: #cbd5e1;
  font-weight: 500;
  cursor: pointer;
}

.sidebar__link--active {
  background-color: #1e293b;
  color: #38bdf8;
  font-weight: 700;
}

.sidebar__logout {
  margin-top: 1rem;
  padding: 0.625rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #ef4444;
  background: transparent;
  color: #fca5a5;
  font-weight: 600;
  cursor: pointer;
}

@media (min-width: 768px) {
  .sidebar {
    display: flex;
  }
}
</style>
