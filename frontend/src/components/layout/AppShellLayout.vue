<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../../stores/authStore';
import AppFooter from './AppFooter.vue';
import BottomNavBar from './BottomNavBar.vue';
import ContextualHelpModal from './ContextualHelpModal.vue';
import SidebarNav from './SidebarNav.vue';
import StaleDataBanner from './StaleDataBanner.vue';

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();

const isHelpOpen = ref(false);

async function handleNavigate(to: string): Promise<void> {
  await router.push(to);
}

async function handleLogout(): Promise<void> {
  authStore.logout();
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

        <StaleDataBanner :is-stale="authStore.isStale" :message="authStore.errorMessage" />
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
  background-color: #f8fafc;
  color: #0f172a;
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
    calc(4.5rem + env(safe-area-inset-bottom, 0px));
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
  margin-bottom: 0.75rem;
}

.app-main__top-spacer {
  flex: 1;
}

.contextual-help-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 9999px;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  color: #0369a1;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
  transition: all 0.15s ease-in-out;
}

.contextual-help-trigger:hover {
  background-color: #f0f9ff;
  border-color: #7dd3fc;
  color: #0284c7;
}

.contextual-help-trigger:focus-visible {
  outline: 2px solid #0284c7;
  outline-offset: 2px;
}

.contextual-help-trigger__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 1.125rem;
  block-size: 1.125rem;
  border-radius: 50%;
  background-color: #e0f2fe;
  color: #0284c7;
  font-size: 0.75rem;
  font-weight: 800;
}

@media (pointer: coarse) {
  .contextual-help-trigger {
    min-block-size: 2.75rem;
    padding: 0.5rem 0.875rem;
  }
}

@media (min-width: 768px) {
  .app-main {
    padding: clamp(1rem, 2vw, 2rem) clamp(1.5rem, 3vw, 3rem);
  }
}
</style>
