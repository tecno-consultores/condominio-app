<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed } from 'vue';
import { getActivePinia } from 'pinia';
import { useAuthStore, type RolUsuario } from '../../stores/authStore';
import { NAV_ICON_PATHS, type NavIconKey } from '../../utils/navIcons';
import ThemeToggleButton from './ThemeToggleButton.vue';

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
  icon: NavIconKey;
  section: 'FINANZAS' | 'COMUNIDAD' | 'OPERACIONES';
  roles?: RolUsuario[];
}

interface SidebarSection {
  key: SidebarLinkItem['section'];
  title: string;
  links: SidebarLinkItem[];
}

const links: SidebarLinkItem[] = [
  {
    id: 'side-dashboard',
    label: 'Resumen Financiero',
    to: '/dashboard',
    icon: 'home',
    section: 'FINANZAS',
  },
  {
    id: 'side-pagar',
    label: 'Reportar Pago',
    to: '/finanzas/reportar-pago',
    icon: 'credit-card',
    section: 'FINANZAS',
  },
  {
    id: 'side-solvencia',
    label: 'Certificado de Solvencia',
    to: '/finanzas/solvencia',
    icon: 'shield-check',
    section: 'FINANZAS',
  },
  {
    id: 'side-revision-pagos',
    label: 'Aprobación de Pagos',
    to: '/tesoreria/pagos',
    icon: 'check-square',
    section: 'FINANZAS',
    roles: ['TESORERO', 'PRESIDENTE'],
  },
  {
    id: 'side-cierre-mensual',
    label: 'Cierre Mensual Contable',
    to: '/tesoreria/cierre',
    icon: 'calculator',
    section: 'FINANZAS',
    roles: ['TESORERO', 'PRESIDENTE'],
  },
  {
    id: 'side-facturacion',
    label: 'Facturación Mensual LPH',
    to: '/tesoreria/facturacion',
    icon: 'receipt',
    section: 'FINANZAS',
    roles: ['TESORERO', 'PRESIDENTE'],
  },
  {
    id: 'side-incidencias',
    label: 'Embudo de Incidencias',
    to: '/incidencias',
    icon: 'alert-circle',
    section: 'COMUNIDAD',
  },
  {
    id: 'side-consultas',
    label: 'Cartas Consulta (Art. 23)',
    to: '/consultas',
    icon: 'vote',
    section: 'COMUNIDAD',
  },
  {
    id: 'side-bitacora',
    label: 'Bitácora de Actas',
    to: '/secretaria/bitacora',
    icon: 'book-open',
    section: 'COMUNIDAD',
  },
  {
    id: 'side-voceros',
    label: 'Galería de Voceros',
    to: '/voceros/galeria',
    icon: 'users',
    section: 'COMUNIDAD',
  },
  {
    id: 'side-reservas',
    label: 'Reserva de Áreas Sociales',
    to: '/reservas/areas',
    icon: 'calendar',
    section: 'COMUNIDAD',
  },
  {
    id: 'side-pases-qr',
    label: 'Pases de Visita QR',
    to: '/accesos/pases',
    icon: 'qr-code',
    section: 'OPERACIONES',
  },
  {
    id: 'side-garita-qr',
    label: 'Escáner Garita QR',
    to: '/operaciones/garita-qr',
    icon: 'scan',
    section: 'OPERACIONES',
    roles: ['CONSERJE', 'PRESIDENTE', 'VOCERO'],
  },
  {
    id: 'side-paqueteria',
    label: 'Paquetería en Garita',
    to: '/operaciones/paqueteria',
    icon: 'package',
    section: 'OPERACIONES',
  },
  {
    id: 'side-tareas',
    label: 'Tareas de Conserjería',
    to: '/operaciones/tareas',
    icon: 'clipboard-check',
    section: 'OPERACIONES',
  },
  {
    id: 'side-estructura',
    label: 'Estructura Física',
    to: '/admin/estructura',
    icon: 'building',
    section: 'OPERACIONES',
    roles: ['PRESIDENTE', 'VICEPRESIDENTE'],
  },
  {
    id: 'side-usuarios',
    label: 'Usuarios Fantasma',
    to: '/admin/usuarios',
    icon: 'user-check',
    section: 'OPERACIONES',
    roles: ['PRESIDENTE', 'VICEPRESIDENTE'],
  },
  {
    id: 'side-junta',
    label: 'Junta de Condominio',
    to: '/admin/junta',
    icon: 'award',
    section: 'OPERACIONES',
    roles: ['PRESIDENTE'],
  },
];

const SECTION_META: Array<{ key: SidebarLinkItem['section']; title: string }> = [
  { key: 'FINANZAS', title: 'Mi Hogar y Finanzas' },
  { key: 'COMUNIDAD', title: 'Comunidad y Gobernanza' },
  { key: 'OPERACIONES', title: 'Operaciones y Junta Directiva' },
];

const effectiveRole = computed<RolUsuario | null>(() => {
  if (props.role) {
    return props.role;
  }
  const pinia = getActivePinia();
  return pinia ? useAuthStore(pinia).userRole : null;
});

function canAccess(link: SidebarLinkItem, activeRole: RolUsuario | null): boolean {
  return !link.roles || (activeRole !== null && link.roles.includes(activeRole));
}

const visibleSections = computed<SidebarSection[]>(() => {
  const activeRole = effectiveRole.value;
  return SECTION_META.map((sec) => ({
    key: sec.key,
    title: sec.title,
    links: links.filter((link) => link.section === sec.key && canAccess(link, activeRole)),
  })).filter((sec) => sec.links.length > 0);
});
</script>

<template>
  <aside id="desktop-sidebar" class="sidebar" aria-label="Menú lateral de escritorio">
    <div class="sidebar__brand">
      <div>
        <strong class="sidebar__title">Condominio App</strong>
        <span class="sidebar__role-badge">{{ effectiveRole || 'RESIDENTE' }}</span>
      </div>
      <ThemeToggleButton button-id="btn-sidebar-theme-toggle" compact />
    </div>

    <p class="sidebar__user">{{ userName }}</p>

    <div class="sidebar__sections">
      <section
        v-for="section in visibleSections"
        :key="section.key"
        class="sidebar__section"
        :aria-label="section.title"
      >
        <h2 class="sidebar__section-title">{{ section.title }}</h2>
        <ul class="sidebar__list">
          <li v-for="link in section.links" :key="link.to">
            <button
              :id="link.id"
              type="button"
              class="sidebar__link"
              :class="{ 'sidebar__link--active': currentPath === link.to }"
              :aria-current="currentPath === link.to ? 'page' : undefined"
              @click="emit('navigate', link.to)"
            >
              <svg
                class="sidebar__icon"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.75"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path v-for="(pathD, idx) in NAV_ICON_PATHS[link.icon]" :key="idx" :d="pathD" />
              </svg>
              <span>{{ link.label }}</span>
            </button>
          </li>
        </ul>
      </section>
    </div>

    <button id="btn-sidebar-logout" type="button" class="sidebar__logout" @click="emit('logout')">
      Cerrar Sesión
    </button>
  </aside>
</template>

<style scoped>
.sidebar {
  display: none;
  width: 17rem;
  flex-shrink: 0;
  background-color: var(--surface-card, #ffffff);
  color: var(--text-primary, #0f172a);
  padding: 1.25rem 0.875rem;
  flex-direction: column;
  border-right: 1px solid var(--border-subtle, #e2e8f0);
}

.sidebar__brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.375rem;
}

.sidebar__title {
  display: block;
  font-size: 1.0625rem;
  color: var(--text-primary, #0f172a);
}

.sidebar__role-badge {
  display: inline-block;
  margin-top: 0.25rem;
  font-size: 0.7rem;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-pill, 9999px);
  background-color: var(--brand-tint, #e0f2fe);
  color: var(--brand-accent, #0369a1);
  font-weight: 700;
}

.sidebar__user {
  font-size: 0.875rem;
  color: var(--text-secondary, #475569);
  margin: 0 0 1.25rem;
}

.sidebar__sections {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  flex: 1;
  overflow-y: auto;
}

.sidebar__section-title {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-tertiary, #475569);
  margin: 0 0 0.375rem 0.5rem;
}

.sidebar__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.sidebar__link {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.75rem;
  min-block-size: 2.5rem;
  border-radius: var(--radius-sm, 0.5rem);
  border: none;
  border-inline-start: 3px solid transparent;
  background: transparent;
  color: var(--text-secondary, #334155);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.sidebar__link:hover {
  background-color: var(--surface-subtle, #f1f5f9);
  color: var(--text-primary, #0f172a);
}

.sidebar__link--active {
  background-color: var(--brand-tint, #e0f2fe);
  border-inline-start-color: var(--brand-accent, #0369a1);
  color: var(--brand-accent, #0369a1);
  font-weight: 600;
}

.sidebar__icon {
  flex-shrink: 0;
}

.sidebar__logout {
  margin-top: 1rem;
  min-block-size: 2.75rem;
  padding: 0.625rem 0.75rem;
  border-radius: var(--radius-sm, 0.5rem);
  border: 1px solid var(--status-danger-border, #ef4444);
  background: transparent;
  color: var(--status-danger-text, #b91c1c);
  font-weight: 600;
  cursor: pointer;
}

.sidebar__logout:hover {
  background-color: var(--status-danger-bg, #fef2f2);
}

@media (min-width: 768px) {
  .sidebar {
    display: flex;
  }
}
</style>
