<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAccessAmenitiesStore } from '../../stores/accessAmenitiesStore';
import { useAuthStore } from '../../stores/authStore';
import { useFinanceStore } from '../../stores/financeStore';
import { useGovernanceStore } from '../../stores/governanceStore';
import { useOperationsStore } from '../../stores/operationsStore';
import AppFooter from './AppFooter.vue';
import BottomNavBar from './BottomNavBar.vue';
import ContextualHelpModal from './ContextualHelpModal.vue';
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
            aria-label="Cerrar aviso de permisos"
            @click="authStore.setRbacNotice(null)"
          >
            Entendido
          </button>
        </div>

        <StaleDataBanner :is-stale="anyStoreStale" :message="staleBannerMessage" />
        <slot />
      </div>
      <AppFooter version="1.0.0" />
    </main>

    <BottomNavBar
      :role="authStore.userRole"
      :current-path="route.path"
      @navigate="handleNavigate"
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
  background-color: var(--surface-canvas, #f8fafc);
  color: var(--text-primary, #0f172a);
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
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.app-main__top-spacer {
  flex: 1;
}

.contextual-help-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  min-block-size: 2.75rem;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-pill, 9999px);
  background-color: var(--surface-card, #ffffff);
  border: 1px solid var(--border-control, #cbd5e1);
  color: var(--brand-accent, #0369a1);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition:
    border-color 0.15s ease-in-out,
    box-shadow 0.15s ease-in-out;
}

.contextual-help-trigger:hover {
  background-color: var(--brand-tint, #f0f9ff);
  border-color: var(--brand-accent, #7dd3fc);
}

.contextual-help-trigger:focus-visible {
  outline: 2px solid var(--brand-accent, #0369a1);
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
  border-radius: var(--radius-sm, 0.5rem);
  background-color: var(--status-warn-bg, #fef3c7);
  border: 1px solid var(--status-warn-border, #f59e0b);
  color: var(--status-warn-text, #78350f);
  font-size: 0.875rem;
  font-weight: 600;
}

.rbac-notice-banner__close {
  padding: 0.375rem 0.75rem;
  min-block-size: 2.25rem;
  border-radius: var(--radius-sm, 0.375rem);
  border: 1px solid var(--status-warn-border, #d97706);
  background-color: var(--surface-card, #ffffff);
  color: var(--status-warn-text, #78350f);
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
  background-color: var(--brand-tint, #e0f2fe);
  color: var(--brand-accent, #0369a1);
  font-size: 0.75rem;
  font-weight: 800;
}

@media (min-width: 768px) {
  .app-main {
    padding: clamp(1rem, 2vw, 2rem) clamp(1.5rem, 3vw, 3rem) 6rem;
  }
}
</style>
