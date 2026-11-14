<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    lines?: number;
    height?: string;
    label?: string;
  }>(),
  {
    lines: 3,
    height: 'auto',
    label: 'Cargando contenido...',
  },
);
</script>

<template>
  <div class="skeleton-card" role="status" aria-busy="true" :style="{ minBlockSize: props.height }">
    <span class="sr-only">{{ props.label }}</span>
    <span class="skeleton-card__bar skeleton-card__bar--heading" aria-hidden="true"></span>
    <span
      v-for="idx in props.lines"
      :key="idx"
      class="skeleton-card__bar"
      :class="{ 'skeleton-card__bar--short': idx === props.lines }"
      aria-hidden="true"
    ></span>
  </div>
</template>

<style scoped>
.skeleton-card {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  padding: 1.25rem;
  border-radius: var(--radius-md, 0.75rem);
  background-color: var(--surface-card, #ffffff);
  border: 1px solid var(--border-subtle, #e2e8f0);
  box-shadow: var(--shadow-card);
}

.skeleton-card__bar {
  display: block;
  block-size: 0.875rem;
  inline-size: 100%;
  border-radius: var(--radius-pill, 9999px);
  background-color: var(--surface-subtle, #e2e8f0);
}

.skeleton-card__bar--heading {
  block-size: 1.25rem;
  inline-size: 48%;
  margin-bottom: 0.25rem;
}

.skeleton-card__bar--short {
  inline-size: 68%;
}

@media (prefers-reduced-motion: no-preference) {
  .skeleton-card__bar {
    background: linear-gradient(
      90deg,
      var(--surface-subtle, #e2e8f0) 25%,
      var(--border-subtle, #cbd5e1) 50%,
      var(--surface-subtle, #e2e8f0) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-shimmer 1.5s infinite linear;
  }

  @keyframes skeleton-shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }
}
</style>
