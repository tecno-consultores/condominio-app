<script setup lang="ts">
defineProps<{
  version?: string;
}>();
</script>

<template>
  <footer id="app-inflow-footer" class="app-footer">
    <p class="app-footer__text">
      Condominio App v{{ version || '1.0.0' }} — Gobernanza &amp; Transparencia Residencial (MIT)
    </p>
  </footer>
</template>

<style scoped>
.app-footer {
  margin-top: auto;
  padding: 1.25rem 1rem;
  border-top: 1px solid #e2e8f0;
  color: #475569;
  font-size: 0.75rem;
  text-align: center;
}

.app-footer__text {
  margin: 0;
}
</style>
