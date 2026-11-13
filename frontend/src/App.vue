<script setup lang="ts">
import { RouterView } from 'vue-router';
</script>

<template>
  <div id="condominio-root">
    <RouterView />
  </div>
</template>

<style>
@media (forced-colors: active) {
  button {
    border: 1px solid ButtonText;
  }

  dialog[open] {
    border: 2px solid CanvasText;
  }
}
</style>
