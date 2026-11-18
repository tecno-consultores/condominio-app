<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, ref } from 'vue';
import { RouterView, useRoute, useRouter } from 'vue-router';
import { useAccessAmenitiesStore } from '../../stores/accessAmenitiesStore';
import { useAuthStore } from '../../stores/authStore';
import { useFinanceStore } from '../../stores/financeStore';
import { useGovernanceStore } from '../../stores/governanceStore';
import { useOperationsStore } from '../../stores/operationsStore';
import AppFooter from './AppFooter.vue';
import BottomNavBar from './BottomNavBar.vue';
import ContextualHelpModal from './ContextualHelpModal.vue';
import MobileNavDrawer from './MobileNavDrawer.vue';
import SidebarNav from './SidebarNav.vue';
import StaleDataBanner from './StaleDataBanner.vue';
import ThemeToggleButton from './ThemeToggleButton.vue';

const authStore = useAuthStore();
const financeStore = useFinanceStore();
const operationsStore = useOperationsStore();
const governanceStore = useGovernanceStore();
const accessAmenitiesStore = useAccessAmenitiesStore();
const route = useRoute();
const router = useRouter();

const isHelpOpen = ref(false);
const isMobileMenuOpen = ref(false);

const anyStoreStale = computed(
  () =>
    authStore.isStale ||
    financeStore.isStale ||
    operationsStore.isStale ||
    governanceStore.isStale ||
    accessAmenitiesStore.isStale,
);

const staleBannerMessage = computed(
  () =>
    (authStore.isStale ? authStore.errorMessage : null) ??
    (financeStore.isStale ? financeStore.errorMessage : null) ??
    (operationsStore.isStale ? operationsStore.errorMessage : null) ??
    (governanceStore.isStale ? governanceStore.error : null) ??
    (accessAmenitiesStore.isStale ? accessAmenitiesStore.error : null) ??
    authStore.errorMessage,
);

async function handleNavigate(to: string): Promise<void> {
  authStore.setRbacNotice(null);
  await router.push(to);
}

async function handleLogout(): Promise<void> {
  isMobileMenuOpen.value = false;
  await authStore.logout();
  await router.push('/login');
}
</script>

<template>
  <div id="app-shell" class="app-shell">
    <SidebarNav
      :user-name="authStore.data?.nombre || 'Residente'"
      :role="authStore.userRole"
      :current-path="route.path"
      @navigate="handleNavigate"
      @logout="handleLogout"
    />

    <main id="app-main-content" class="app-main">
      <div class="app-main__body">
        <header class="app-main__top-bar">
          <button
            id="btn-mobile-menu"
            type="button"
            class="mobile-top-trigger"
            aria-label="Abrir menú completo"
            :aria-expanded="isMobileMenuOpen ? 'true' : 'false'"
            aria-controls="mobile-nav-drawer"
            @click="isMobileMenuOpen = true"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              aria-hidden="true"
            >
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            <span>Menú</span>
          </button>

          <div class="app-main__top-spacer"></div>

          <ThemeToggleButton button-id="btn-theme-toggle" />
          <button
            id="btn-contextual-help"
            type="button"
            class="contextual-help-trigger"
            aria-label="Abrir ayuda de esta pantalla"
            @click="isHelpOpen = true"
          >
            <span class="contextual-help-trigger__icon" aria-hidden="true">?</span>
            <span class="contextual-help-trigger__label">Ayuda</span>
          </button>
          <button
            id="btn-mobile-logout"
            type="button"
            class="mobile-logout-trigger"
            aria-label="Salir y cerrar sesión"
            @click="handleLogout"
          >
            Salir
          </button>
        </header>

        <div
          v-if="authStore.rbacNotice"
          id="rbac-notice-banner"
          class="rbac-notice-banner"
          role="status"
          aria-live="polite"
        >
          <span class="rbac-notice-banner__text">{{ authStore.rbacNotice }}</span>
          <button
            id="btn-dismiss-rbac-notice"
            type="button"
            class="rbac-notice-banner__close"
            aria-label="Entendido, cerrar aviso de permisos"
            @click="authStore.setRbacNotice(null)"
          >
            Entendido
          </button>
        </div>

        <StaleDataBanner :is-stale="anyStoreStale" :message="staleBannerMessage" />
        <slot>
          <RouterView />
        </slot>
      </div>
      <AppFooter version="1.0.0" />
    </main>

    <BottomNavBar
      :role="authStore.userRole"
      :current-path="route.path"
      @navigate="handleNavigate"
    />

    <MobileNavDrawer
      :open="isMobileMenuOpen"
      :user-name="authStore.data?.nombre || 'Residente'"
      :role="authStore.userRole"
      :current-path="route.path"
      @close="isMobileMenuOpen = false"
      @navigate="handleNavigate"
      @logout="handleLogout"
    />

    <ContextualHelpModal
      :open="isHelpOpen"
      :path="route.path"
      :role="authStore.userRole"
      @close="isHelpOpen = false"
    />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100dvh;
  background-color: var(--surface-canvas);
  color: var(--text-primary);
}

.app-main {
  flex: 1;
  min-inline-size: 0;
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
  container-type: inline-size;
  container-name: main-canvas;
  padding: clamp(0.75rem, 2vw, 1.5rem) clamp(1rem, 3vw, 2.5rem)
    calc(9.5rem + env(safe-area-inset-bottom, 0px));
}

.app-main__body {
  flex: 1;
  width: 100%;
  max-inline-size: 76rem;
  margin-inline: auto;
}

.app-main__top-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.app-main__top-spacer {
  flex: 1;
}

.mobile-top-trigger,
.mobile-logout-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  min-block-size: 2.75rem;
  min-inline-size: 2.75rem;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}

.mobile-top-trigger {
  border: 1px solid var(--border-control);
  background-color: var(--surface-card);
  color: var(--text-primary);
  box-shadow: var(--shadow-card);
}

.mobile-logout-trigger {
  border: 1px solid var(--status-danger-border);
  background-color: var(--status-danger-bg);
  color: var(--status-danger-text);
}

.contextual-help-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  min-block-size: 2.75rem;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-pill);
  background-color: var(--surface-card);
  border: 1px solid var(--border-control);
  color: var(--brand-accent);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition:
    border-color 0.15s ease-in-out,
    box-shadow 0.15s ease-in-out;
}

.contextual-help-trigger:hover {
  background-color: var(--brand-tint);
  border-color: var(--brand-accent);
}

.contextual-help-trigger:focus-visible {
  outline: 2px solid var(--brand-accent);
  outline-offset: 2px;
}

.rbac-notice-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
  padding: 0.625rem 0.875rem;
  border-radius: var(--radius-sm);
  background-color: var(--status-warn-bg);
  border: 1px solid var(--status-warn-border);
  color: var(--status-warn-text);
  font-size: 0.875rem;
  font-weight: 600;
}

.rbac-notice-banner__close {
  padding: 0.375rem 0.75rem;
  min-block-size: 2.75rem;
  min-inline-size: 2.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--status-warn-border);
  background-color: var(--surface-card);
  color: var(--status-warn-text);
  font-size: 0.8125rem;
  font-weight: 700;
  cursor: pointer;
}

.contextual-help-trigger__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 1.25rem;
  block-size: 1.25rem;
  border-radius: 50%;
  background-color: var(--brand-tint);
  color: var(--brand-accent);
  font-size: 0.75rem;
  font-weight: 800;
}

@media (min-width: 768px) {
  .app-main {
    padding: clamp(1rem, 2vw, 2rem) clamp(1.5rem, 3vw, 3rem) 6rem;
  }

  .mobile-top-trigger,
  .mobile-logout-trigger {
    display: none;
  }
}
</style>
