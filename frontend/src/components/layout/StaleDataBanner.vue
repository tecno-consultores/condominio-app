<script setup lang="ts">
defineProps<{
  isStale: boolean;
  message?: string | null;
}>();
</script>

<template>
  <div v-if="isStale" id="stale-data-banner" class="banner--stale" role="status" aria-live="polite">
    <span class="banner--stale__badge">Modo sin conexión</span>
    <span class="banner--stale__text">
      {{ message || 'Mostrando los últimos datos sincronizados. Reintentando conexión...' }}
    </span>
  </div>
</template>

<style scoped>
.banner--stale {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  margin-bottom: 1rem;
  border-radius: 0.5rem;
  background-color: #fff8e1;
  border: 1px solid #f59e0b;
  color: #78350f;
  font-size: 0.875rem;
}

.banner--stale__badge {
  font-weight: 700;
  text-transform: uppercase;
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  background-color: #fde68a;
}
</style>
