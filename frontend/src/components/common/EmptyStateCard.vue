<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    title: string;
    description: string;
    actionLabel?: string;
    icon?: 'inbox' | 'check' | 'doc' | 'users' | 'sparkle';
  }>(),
  {
    actionLabel: undefined,
    icon: 'inbox',
  },
);

const emit = defineEmits<{
  (e: 'action'): void;
}>();

const ICON_PATHS: Record<NonNullable<typeof props.icon>, readonly string[]> = {
  inbox: [
    'M4 13h4l2 3h4l2-3h4',
    'M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z',
  ],
  check: ['M22 11.08V12a10 10 0 1 1-5.93-9.14', 'm9 11 3 3L22 4'],
  doc: [
    'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z',
    'M14 2v6h6',
    'M9 13h6',
    'M9 17h4',
  ],
  users: [
    'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2',
    'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z',
    'M22 21v-2a4 4 0 0 0-3-3.87',
    'M16 3.13a4 4 0 0 1 0 7.75',
  ],
  sparkle: [
    'm12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3Z',
  ],
};
</script>

<template>
  <section class="empty-state-card" role="status" aria-live="polite">
    <div class="empty-state-card__art" aria-hidden="true">
      <svg
        aria-hidden="true"
        width="36"
        height="36"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path v-for="(d, idx) in ICON_PATHS[props.icon]" :key="idx" :d="d" />
      </svg>
    </div>
    <h3 class="empty-state-card__title">{{ props.title }}</h3>
    <p class="empty-state-card__desc">{{ props.description }}</p>
    <button
      v-if="props.actionLabel"
      type="button"
      class="empty-state-card__cta"
      @click="emit('action')"
    >
      {{ props.actionLabel }}
    </button>
  </section>
</template>

<style scoped>
.empty-state-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 2rem 1.5rem;
  border-radius: var(--radius-lg, 1rem);
  background-color: var(--surface-card, #ffffff);
  border: 1px dashed var(--border-control, #94a3b8);
  box-shadow: var(--shadow-card);
  color: var(--text-primary, #0f172a);
}

.empty-state-card__art {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  inline-size: 4rem;
  block-size: 4rem;
  border-radius: 50%;
  background-color: var(--brand-tint, #e0f2fe);
  color: var(--brand-accent, #0369a1);
  margin-bottom: 0.875rem;
}

.empty-state-card__title {
  margin: 0 0 0.375rem;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary, #0f172a);
  text-wrap: balance;
}

.empty-state-card__desc {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-secondary, #475569);
  max-inline-size: 50ch;
  text-wrap: pretty;
}

.empty-state-card__cta {
  margin-top: 1rem;
  min-block-size: 2.75rem;
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-sm, 0.5rem);
  border: none;
  background-color: var(--brand-600, #0369a1);
  color: #ffffff;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}
</style>
