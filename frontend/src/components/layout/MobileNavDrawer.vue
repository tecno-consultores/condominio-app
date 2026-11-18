<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useTopLayerDialog } from '../../composables/useTopLayerDialog';
import type { RolUsuario } from '../../stores/authStore';
import { NAV_ICON_PATHS } from '../../utils/navIcons';
import { getVisibleNavigationSections } from '../../utils/navigationCatalog';
import ThemeToggleButton from './ThemeToggleButton.vue';

const props = defineProps<{
  open: boolean;
  userName: string;
  role: RolUsuario | null;
  currentPath: string;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'navigate', to: string): void;
  (e: 'logout'): void;
}>();

const dialogRef = ref<HTMLDialogElement | null>(null);
const visibleSections = computed(() => getVisibleNavigationSections(props.role));

const { dialogProps, onPointerDown, onPointerUp, onBackdropClick } = useTopLayerDialog({
  dialogRef,
  isOpen: () => props.open,
  onClose: () => emit('close'),
  unmountsWhenClosed: true,
});

function handleNavigate(to: string): void {
  emit('navigate', to);
  emit('close');
}

function handleLogoutClick(): void {
  emit('close');
  emit('logout');
}
</script>

<template>
  <dialog
    v-if="open"
    id="mobile-nav-drawer"
    ref="dialogRef"
    v-bind="dialogProps"
    class="mobile-drawer"
    aria-label="Menú completo de navegación"
    @cancel.prevent="emit('close')"
    @pointerdown="onPointerDown"
    @pointerup="onPointerUp"
    @click="onBackdropClick"
  >
    <div class="mobile-drawer__sheet">
      <header class="mobile-drawer__header">
        <div>
          <strong class="mobile-drawer__title">Condominio App</strong>
          <span class="mobile-drawer__role">{{ role || 'RESIDENTE' }} · {{ userName }}</span>
        </div>
        <button
          id="btn-close-mobile-drawer"
          type="button"
          class="mobile-drawer__close"
          aria-label="Cerrar menú de navegación"
          autofocus
          @click="emit('close')"
        >
          ✕
        </button>
      </header>

      <nav class="mobile-drawer__nav" aria-label="Rutas autorizadas móvil">
        <section
          v-for="section in visibleSections"
          :key="section.key"
          class="mobile-drawer__section"
          :aria-label="section.title"
        >
          <h2 class="mobile-drawer__section-title">{{ section.title }}</h2>
          <ul class="mobile-drawer__list">
            <li v-for="link in section.links" :key="link.to">
              <button
                :id="`drawer-${link.id}`"
                type="button"
                class="mobile-drawer__link"
                :class="{ 'mobile-drawer__link--active': currentPath === link.to }"
                :aria-current="currentPath === link.to ? 'page' : undefined"
                @click="handleNavigate(link.to)"
              >
                <svg
                  class="mobile-drawer__icon"
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
      </nav>

      <footer class="mobile-drawer__footer">
        <ThemeToggleButton button-id="btn-drawer-theme-toggle" compact />
        <button
          id="btn-mobile-drawer-logout"
          type="button"
          class="mobile-drawer__logout"
          @click="handleLogoutClick"
        >
          Cerrar sesión
        </button>
      </footer>
    </div>
  </dialog>
</template>

<style scoped>
.mobile-drawer {
  inset: 0 auto 0 0;
  inline-size: min(21rem, 88dvw);
  max-inline-size: calc(100dvw - 1.5rem);
  block-size: 100dvh;
  max-block-size: 100dvh;
  margin: 0;
  padding: 0;
  border: none;
  border-inline-end: 1px solid var(--border-subtle);
  background-color: var(--surface-card);
  color: var(--text-primary);
  box-shadow: var(--shadow-modal);
}

.mobile-drawer__sheet {
  display: flex;
  flex-direction: column;
  block-size: 100%;
  padding: 1rem;
  gap: 1rem;
  overflow-y: auto;
}

.mobile-drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-subtle);
}

.mobile-drawer__title {
  display: block;
  font-size: 1.0625rem;
  color: var(--text-primary);
}

.mobile-drawer__role {
  display: block;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.mobile-drawer__close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-inline-size: 2.75rem;
  min-block-size: 2.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-subtle);
  color: var(--text-primary);
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
}

.mobile-drawer__nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.mobile-drawer__section-title {
  margin: 0 0 0.375rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary);
}

.mobile-drawer__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.mobile-drawer__link {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  min-block-size: 2.75rem;
  padding: 0.5rem 0.75rem;
  border: none;
  border-inline-start: 3px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.9375rem;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
}

.mobile-drawer__link--active {
  background-color: var(--brand-tint);
  border-inline-start-color: var(--brand-accent);
  color: var(--brand-accent);
  font-weight: 700;
}

.mobile-drawer__icon {
  flex-shrink: 0;
}

.mobile-drawer__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-subtle);
}

.mobile-drawer__logout {
  flex: 1;
  min-block-size: 2.75rem;
  padding: 0.625rem 0.875rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--status-danger-border);
  background-color: var(--status-danger-bg);
  color: var(--status-danger-text);
  font-weight: 700;
  cursor: pointer;
}
</style>
