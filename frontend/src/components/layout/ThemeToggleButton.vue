<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (C) 2026 Condominio App Contributors -->

<script setup lang="ts">
import { computed } from 'vue';
import { useThemeMode } from '../../composables/useThemeMode';

const props = withDefaults(
  defineProps<{
    buttonId?: string;
    compact?: boolean;
  }>(),
  {
    buttonId: 'btn-theme-toggle',
    compact: false,
  },
);

const { resolvedTheme, toggleThemeMode } = useThemeMode();

const isDark = computed(() => resolvedTheme.value === 'dark');
const ariaLabel = computed(() => (isDark.value ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'));
const visibleLabel = computed(() => (isDark.value ? 'Modo claro' : 'Modo oscuro'));
</script>

<template>
  <button
    :id="props.buttonId"
    type="button"
    class="theme-toggle-btn"
    :class="{ 'theme-toggle-btn--compact': props.compact }"
    :aria-label="ariaLabel"
    :aria-pressed="isDark"
    :title="ariaLabel"
    @click="toggleThemeMode"
  >
    <svg
      v-if="isDark"
      class="theme-toggle-btn__icon"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.75"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="4" />
      <path
        d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"
      />
    </svg>
    <svg
      v-else
      class="theme-toggle-btn__icon"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.75"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </svg>
    <span v-if="!props.compact" class="theme-toggle-btn__label">{{ visibleLabel }}</span>
  </button>
</template>

<style scoped>
.theme-toggle-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  min-inline-size: 2.75rem;
  min-block-size: 2.75rem;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-pill, 9999px);
  background-color: var(--surface-card, #ffffff);
  border: 1px solid var(--border-control, #64748b);
  color: var(--text-primary, #0f172a);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease;
}

.theme-toggle-btn--compact {
  padding: 0.375rem;
}

.theme-toggle-btn:hover {
  background-color: var(--brand-tint, #f0f9ff);
  border-color: var(--brand-accent, #0369a1);
}

.theme-toggle-btn:focus-visible {
  outline: 2px solid var(--brand-accent, #0369a1);
  outline-offset: 2px;
}

.theme-toggle-btn__icon {
  flex-shrink: 0;
}

@media (max-width: 479px) {
  .theme-toggle-btn__label {
    display: none;
  }
}
</style>
