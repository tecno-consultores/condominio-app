<script setup lang="ts">
import { computed } from 'vue';
import type { RolUsuario } from '../../stores/authStore';

export interface NavItem {
  id: string;
  label: string;
  to: string;
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
      { id: 'nav-tareas', label: 'Tareas Hoy', to: '/operaciones/tareas' },
      { id: 'nav-incidencias', label: 'Incidencias', to: '/incidencias' },
    ];
  }
  if (props.role === 'TESORERO') {
    return [
      { id: 'nav-inicio', label: 'Inicio', to: '/dashboard' },
      { id: 'nav-revision', label: 'Aprobar Pagos', to: '/tesoreria/pagos' },
      { id: 'nav-cierre', label: 'Cierre Mes', to: '/tesoreria/cierre' },
      { id: 'nav-incidencias', label: 'Incidencias', to: '/incidencias' },
    ];
  }
  if (props.role === 'PRESIDENTE' || props.role === 'VICEPRESIDENTE') {
    return [
      { id: 'nav-inicio', label: 'Inicio', to: '/dashboard' },
      { id: 'nav-usuarios', label: 'Usuarios', to: '/admin/usuarios' },
      { id: 'nav-estructura', label: 'Estructura', to: '/admin/estructura' },
      { id: 'nav-incidencias', label: 'Incidencias', to: '/incidencias' },
    ];
  }
  return [
    { id: 'nav-inicio', label: 'Inicio', to: '/dashboard' },
    { id: 'nav-pagar', label: 'Reportar Pago', to: '/finanzas/reportar-pago' },
    { id: 'nav-incidencias', label: 'Incidencias', to: '/incidencias' },
    { id: 'nav-bitacora', label: 'Bitácora', to: '/secretaria/bitacora' },
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
  min-block-size: 3.75rem;
  padding: 0.25rem 0.5rem calc(0.25rem + env(safe-area-inset-bottom, 0px));
  background-color: #0f172a;
  border-top: 1px solid #1e293b;
}

.bottom-nav__btn {
  flex: 1;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0.375rem 0.5rem;
  color: #94a3b8;
  background: transparent;
  border: none;
  border-radius: 0.5rem;
  font-size: clamp(0.7rem, 2.2vw, 0.8rem);
  font-weight: 500;
  cursor: pointer;
}

@media (pointer: coarse) {
  .bottom-nav__btn {
    min-block-size: 2.75rem;
    padding: 0.5rem;
  }
}

.bottom-nav__btn--active {
  color: #38bdf8;
  font-weight: 700;
  background-color: rgba(56, 189, 248, 0.12);
}

@media (min-width: 768px) {
  .bottom-nav {
    display: none;
  }
}
</style>
