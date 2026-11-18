<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed } from 'vue';
import { getActivePinia } from 'pinia';
import { useAuthStore, type RolUsuario } from '../../stores/authStore';
import { NAV_ICON_PATHS } from '../../utils/navIcons';
import { getVisibleNavigationSections } from '../../utils/navigationCatalog';
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

const effectiveRole = computed<RolUsuario | null>(() => {
  if (props.role) {
    return props.role;
  }
  const pinia = getActivePinia();
  return pinia ? useAuthStore(pinia).userRole : null;
});

const visibleSections = computed(() => getVisibleNavigationSections(effectiveRole.value));
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
  background-color: var(--surface-card);
  color: var(--text-primary);
  padding: 1.25rem 0.875rem;
  flex-direction: column;
  border-right: 1px solid var(--border-subtle);
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
  color: var(--text-primary);
}

.sidebar__role-badge {
  display: inline-block;
  margin-top: 0.25rem;
  font-size: 0.7rem;
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-pill);
  background-color: var(--brand-tint);
  color: var(--brand-accent);
  font-weight: 700;
}

.sidebar__user {
  font-size: 0.875rem;
  color: var(--text-secondary);
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
  color: var(--text-tertiary);
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
  min-block-size: 2.75rem;
  border-radius: var(--radius-sm);
  border: none;
  border-inline-start: 3px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.15s ease;
}

.sidebar__link:hover {
  background-color: var(--surface-subtle);
  color: var(--text-primary);
}

.sidebar__link--active {
  background-color: var(--brand-tint);
  border-inline-start-color: var(--brand-accent);
  color: var(--brand-accent);
  font-weight: 600;
}

.sidebar__icon {
  flex-shrink: 0;
}

.sidebar__logout {
  margin-top: 1rem;
  min-block-size: 2.75rem;
  padding: 0.625rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--status-danger-border);
  background: transparent;
  color: var(--status-danger-text);
  font-weight: 600;
  cursor: pointer;
}

.sidebar__logout:hover {
  background-color: var(--status-danger-bg);
}

@media (min-width: 768px) {
  .sidebar {
    display: flex;
  }
}
</style>
