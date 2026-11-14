// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import SkeletonCard from './SkeletonCard.vue';

describe('SkeletonCard.vue', () => {
  it('renderiza placeholder estable aria-busy=true respetando número de líneas y altura', () => {
    const wrapper = mount(SkeletonCard, {
      props: { lines: 4, height: '140px', label: 'Cargando recibos...' },
    });

    const card = wrapper.find('.skeleton-card');
    expect(card.attributes('role')).toBe('status');
    expect(card.attributes('aria-busy')).toBe('true');
    expect(card.attributes('style')).toContain('140px');
    expect(wrapper.text()).toContain('Cargando recibos...');
    // 1 heading bar + 4 line bars = 5
    expect(wrapper.findAll('.skeleton-card__bar').length).toBe(5);

    const defaults = mount(SkeletonCard);
    expect(defaults.findAll('.skeleton-card__bar').length).toBe(4);
  });
});
