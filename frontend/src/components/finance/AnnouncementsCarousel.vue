<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ComunicadoDTO } from '../../stores/financeStore';
import { isSafeMediaUrl } from '../../utils/security';

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

const safeExternalLink = computed<string | null>(() => {
  const link = currentItem.value?.enlace_externo;
  if (!link || !isSafeMediaUrl(link)) {
    return null;
  }
  return link.trim();
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
        <span class="carousel-card__counter tabular-nums"
          >{{ activeIndex + 1 }} / {{ items.length }}</span
        >
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
      <h3 class="carousel-card__item-title">{{ currentItem.titulo }}</h3>
      <p class="carousel-card__item-text">{{ currentItem.contenido }}</p>
      <a
        v-if="safeExternalLink"
        id="carousel-external-link"
        :href="safeExternalLink"
        target="_blank"
        rel="noopener noreferrer"
        class="carousel-card__link"
      >
        Ver documento oficial
      </a>
    </article>
    <p v-else class="carousel-card__empty">No hay comunicados oficiales publicados hoy.</p>
  </section>
</template>

<style scoped>
.carousel-card {
  padding: 1.125rem;
  border-radius: var(--radius-md);
  background-color: var(--surface-card);
  border: 1px solid var(--border-subtle);
  margin-bottom: 1.25rem;
  box-shadow: var(--shadow-card);
}

.carousel-card__header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.625rem;
}

.carousel-card__title {
  margin: 0;
  font-size: 0.95rem;
  color: var(--text-primary);
}

.carousel-card__controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.carousel-card__btn {
  min-block-size: 2.75rem;
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-control);
  background-color: var(--surface-subtle);
  color: var(--text-primary);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
}

.carousel-card__counter {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-weight: 600;
}

.carousel-card__item-title {
  margin: 0 0 0.25rem;
  font-size: 1rem;
  color: var(--text-primary);
}

.carousel-card__item-text {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.carousel-card__link {
  display: inline-flex;
  align-items: center;
  min-block-size: 2.75rem;
  margin-top: 0.375rem;
  color: var(--brand-accent);
  font-size: 0.875rem;
  font-weight: 600;
}

.carousel-card__empty {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-secondary);
}
</style>
