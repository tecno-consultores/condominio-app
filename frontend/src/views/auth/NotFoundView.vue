<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { useRouter } from 'vue-router';
import ThemeToggleButton from '../../components/layout/ThemeToggleButton.vue';
import { useAuthStore } from '../../stores/authStore';

const authStore = useAuthStore();
const router = useRouter();

async function goHome(): Promise<void> {
  if (authStore.isActiveUser) {
    await router.push('/dashboard');
    return;
  }
  if (authStore.isGhostUser) {
    await router.push('/espera-aprobacion');
    return;
  }
  await router.push('/login');
}
</script>

<template>
  <main class="not-found-page">
    <section id="not-found-card" class="not-found-card" aria-labelledby="not-found-heading">
      <div class="not-found-card__top">
        <span class="not-found-card__code">Error 404</span>
        <ThemeToggleButton button-id="btn-theme-toggle" compact />
      </div>
      <h1 id="not-found-heading" class="not-found-card__title">Página no encontrada</h1>
      <p class="not-found-card__desc">
        La ruta solicitada no existe o fue reubicada dentro del portal del condominio.
      </p>
      <button id="btn-go-home" type="button" class="not-found-card__btn" @click="goHome">
        Volver al inicio
      </button>
    </section>
  </main>
</template>

<style scoped>
.not-found-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 1rem;
  background-color: var(--surface-canvas);
  color: var(--text-primary);
}

.not-found-card {
  width: 100%;
  max-width: 440px;
  padding: 2rem 1.5rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
  border-block-start: 4px solid var(--brand-accent);
  background-color: var(--surface-card);
  box-shadow: var(--surface-hairline), var(--shadow-elevated);
  text-align: center;
}

.not-found-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.not-found-card__code {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-pill);
  background-color: var(--status-warn-bg);
  color: var(--status-warn-text);
  font-size: 0.75rem;
  font-weight: 700;
}

.not-found-card__title {
  margin: 0 0 0.5rem;
  font-size: 1.35rem;
  color: var(--text-primary);
}

.not-found-card__desc {
  margin: 0 0 1.5rem;
  font-size: 0.9375rem;
  color: var(--text-secondary);
}

.not-found-card__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-block-size: 2.75rem;
  min-inline-size: 2.75rem;
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: var(--radius-sm);
  background-color: var(--brand-600);
  color: var(--text-on-accent);
  font-weight: 700;
  cursor: pointer;
}
</style>
