<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ComunicadoDTO } from '../../stores/financeStore';
import { sanitizeUntrustedText } from '../../utils/security';

const props = defineProps<{
  items: ComunicadoDTO[];
}>();

const activeIndex = ref(0);

const currentItem = computed<ComunicadoDTO | null>(() => {
  if (props.items.length === 0) {
    return null;
  }
  const safeIdx = Math.min(activeIndex.value, props.items.length - 1);
  return props.items[safeIdx]!;
});

function prevSlide(): void {
  activeIndex.value = (activeIndex.value - 1 + props.items.length) % props.items.length;
}

function nextSlide(): void {
  activeIndex.value = (activeIndex.value + 1) % props.items.length;
}
</script>

<template>
  <section
    id="announcements-carousel"
    class="carousel-card"
    aria-label="Cartelera oficial de comunicados"
  >
    <div class="carousel-card__header">
      <h2 class="carousel-card__title">Cartelera Oficial</h2>
      <div v-if="items.length > 1" class="carousel-card__controls">
        <button
          id="btn-carousel-prev"
          type="button"
          class="carousel-card__btn"
          aria-label="Comunicado anterior"
          @click="prevSlide"
        >
          Anterior
        </button>
        <span class="carousel-card__counter">{{ activeIndex + 1 }} / {{ items.length }}</span>
        <button
          id="btn-carousel-next"
          type="button"
          class="carousel-card__btn"
          aria-label="Siguiente comunicado"
          @click="nextSlide"
        >
          Siguiente
        </button>
      </div>
    </div>

    <article v-if="currentItem" class="carousel-card__body">
      <h3 class="carousel-card__item-title">{{ sanitizeUntrustedText(currentItem.titulo) }}</h3>
      <p class="carousel-card__item-text">{{ sanitizeUntrustedText(currentItem.contenido) }}</p>
    </article>
    <p v-else class="carousel-card__empty">No hay comunicados oficiales publicados hoy.</p>
  </section>
</template>

<style scoped>
.carousel-card {
  padding: 1.125rem;
  border-radius: 0.75rem;
  background-color: #ffffff;
  border: 1px solid #cbd5e1;
  margin-bottom: 1.25rem;
}

.carousel-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.625rem;
}

.carousel-card__title {
  margin: 0;
  font-size: 0.95rem;
  color: #0f172a;
}

.carousel-card__controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.carousel-card__btn {
  min-height: 36px;
  padding: 0.25rem 0.625rem;
  border-radius: 0.375rem;
  border: 1px solid #cbd5e1;
  background-color: #f8fafc;
  color: #0f172a;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
}

.carousel-card__counter {
  font-size: 0.75rem;
  color: #475569;
  font-weight: 600;
}

.carousel-card__item-title {
  margin: 0 0 0.25rem;
  font-size: 1rem;
  color: #0f172a;
}

.carousel-card__item-text {
  margin: 0;
  font-size: 0.875rem;
  color: #334155;
}

.carousel-card__empty {
  margin: 0;
  font-size: 0.85rem;
  color: #64748b;
}
</style>
