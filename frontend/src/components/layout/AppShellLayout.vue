<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../../stores/authStore';
import AppFooter from './AppFooter.vue';
import BottomNavBar from './BottomNavBar.vue';
import SidebarNav from './SidebarNav.vue';
import StaleDataBanner from './StaleDataBanner.vue';

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();

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
  padding: clamp(1rem, 2.5vw, 2rem) clamp(1rem, 3vw, 2.5rem)
    calc(4.5rem + env(safe-area-inset-bottom, 0px));
}

.app-main__body {
  flex: 1;
  width: 100%;
  max-inline-size: 76rem;
  margin-inline: auto;
}

@media (min-width: 768px) {
  .app-main {
    padding: clamp(1.5rem, 2.5vw, 2.5rem) clamp(1.5rem, 3vw, 3rem);
  }
}
</style>
