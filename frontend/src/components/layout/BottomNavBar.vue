<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed } from 'vue';
import type { RolUsuario } from '../../stores/authStore';
import { NAV_ICON_PATHS, type NavIconKey } from '../../utils/navIcons';

export interface NavItem {
  id: string;
  label: string;
  to: string;
  icon: NavIconKey;
}

const props = defineProps<{
  role: RolUsuario | null;
  currentPath: string;
}>();

const emit = defineEmits<{
  (e: 'navigate', to: string): void;
}>();

const items = computed<NavItem[]>(() => {
  if (props.role === 'CONSERJE') {
    return [
      {
        id: 'nav-tareas',
        label: 'Tareas Hoy',
        to: '/operaciones/tareas',
        icon: 'clipboard-check',
      },
      { id: 'nav-incidencias', label: 'Incidencias', to: '/incidencias', icon: 'alert-circle' },
    ];
  }
  if (props.role === 'TESORERO') {
    return [
      { id: 'nav-inicio', label: 'Inicio', to: '/dashboard', icon: 'home' },
      {
        id: 'nav-revision',
        label: 'Aprobar Pagos',
        to: '/tesoreria/pagos',
        icon: 'check-square',
      },
      { id: 'nav-cierre', label: 'Cierre Mes', to: '/tesoreria/cierre', icon: 'calculator' },
      { id: 'nav-incidencias', label: 'Incidencias', to: '/incidencias', icon: 'alert-circle' },
    ];
  }
  if (props.role === 'PRESIDENTE' || props.role === 'VICEPRESIDENTE') {
    return [
      { id: 'nav-inicio', label: 'Inicio', to: '/dashboard', icon: 'home' },
      { id: 'nav-usuarios', label: 'Usuarios', to: '/admin/usuarios', icon: 'user-check' },
      { id: 'nav-estructura', label: 'Estructura', to: '/admin/estructura', icon: 'building' },
      { id: 'nav-incidencias', label: 'Incidencias', to: '/incidencias', icon: 'alert-circle' },
    ];
  }
  return [
    { id: 'nav-inicio', label: 'Inicio', to: '/dashboard', icon: 'home' },
    {
      id: 'nav-pagar',
      label: 'Reportar Pago',
      to: '/finanzas/reportar-pago',
      icon: 'credit-card',
    },
    { id: 'nav-incidencias', label: 'Incidencias', to: '/incidencias', icon: 'alert-circle' },
    { id: 'nav-bitacora', label: 'Bitácora', to: '/secretaria/bitacora', icon: 'book-open' },
  ];
});
</script>

<template>
  <nav id="mobile-bottom-nav" class="bottom-nav" aria-label="Navegación principal móvil">
    <button
      v-for="item in items"
      :id="item.id"
      :key="item.to"
      type="button"
      class="bottom-nav__btn"
      :class="{ 'bottom-nav__btn--active': currentPath === item.to }"
      :aria-current="currentPath === item.to ? 'page' : undefined"
      @click="emit('navigate', item.to)"
    >
      <span class="bottom-nav__pill">
        <svg
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
          <path v-for="(pathD, idx) in NAV_ICON_PATHS[item.icon]" :key="idx" :d="pathD" />
        </svg>
      </span>
      <span class="bottom-nav__label">{{ item.label }}</span>
    </button>
  </nav>
</template>

<style scoped>
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 40;
  display: flex;
  justify-content: space-around;
  align-items: center;
  min-block-size: 4rem;
  padding: 0.25rem 0.5rem calc(0.25rem + env(safe-area-inset-bottom, 0px));
  background-color: var(--surface-card, #ffffff);
  border-top: 1px solid var(--border-subtle, #e2e8f0);
  box-shadow: var(--shadow-elevated);
}

.bottom-nav__btn {
  flex: 1;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.125rem;
  min-inline-size: 2.75rem;
  min-block-size: 2.75rem;
  padding: 0.25rem 0.5rem;
  color: var(--text-secondary, #475569);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm, 0.5rem);
  font-size: clamp(0.72rem, 2.2vw, 0.8rem);
  font-weight: 500;
  cursor: pointer;
}

.bottom-nav__pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.2rem 0.85rem;
  border-radius: var(--radius-pill, 9999px);
  background-color: transparent;
  transition: background-color 0.16s ease;
}

@media (prefers-reduced-motion: no-preference) {
  .bottom-nav__pill {
    transition:
      background-color 0.16s ease,
      transform 0.18s cubic-bezier(0.2, 0, 0, 1);
  }

  .bottom-nav__btn--active .bottom-nav__pill {
    transform: translateY(-1px);
  }
}

.bottom-nav__btn--active {
  color: var(--brand-accent, #0369a1);
  font-weight: 700;
}

.bottom-nav__btn--active .bottom-nav__pill {
  background-color: var(--brand-tint, #e0f2fe);
}

@media (min-width: 768px) {
  .bottom-nav {
    display: none;
  }
}
</style>
