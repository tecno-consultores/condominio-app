<script setup lang="ts">
import type { RolUsuario } from '../../stores/authStore';

defineProps<{
  userName: string;
  role: RolUsuario | null;
  currentPath: string;
}>();

const emit = defineEmits<{
  (e: 'navigate', to: string): void;
  (e: 'logout'): void;
}>();

const links = [
  { id: 'side-dashboard', label: 'Resumen Financiero', to: '/dashboard' },
  { id: 'side-pagar', label: 'Reportar Pago', to: '/finanzas/reportar-pago' },
  { id: 'side-solvencia', label: 'Certificado de Solvencia', to: '/finanzas/solvencia' },
  { id: 'side-facturacion', label: 'Facturación Mensual LPH', to: '/tesoreria/facturacion' },
  { id: 'side-incidencias', label: 'Embudo de Incidencias', to: '/incidencias' },
  { id: 'side-tareas', label: 'Tareas de Conserjería', to: '/operaciones/tareas' },
  { id: 'side-voceros', label: 'Galería de Voceros', to: '/voceros/galeria' },
  { id: 'side-bitacora', label: 'Bitácora de Actas', to: '/secretaria/bitacora' },
  { id: 'side-estructura', label: 'Estructura Física', to: '/admin/estructura' },
  { id: 'side-usuarios', label: 'Usuarios Fantasma', to: '/admin/usuarios' },
  { id: 'side-junta', label: 'Junta de Condominio', to: '/admin/junta' },
];
</script>

<template>
  <aside id="desktop-sidebar" class="sidebar" aria-label="Menú lateral de escritorio">
    <div class="sidebar__brand">
      <strong class="sidebar__title">Condominio App</strong>
      <span class="sidebar__role-badge">{{ role || 'RESIDENTE' }}</span>
    </div>

    <p class="sidebar__user">{{ userName }}</p>

    <ul class="sidebar__list">
      <li v-for="link in links" :key="link.to">
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
