// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import EmptyStateCard from './EmptyStateCard.vue';

describe('EmptyStateCard.vue', () => {
  it('renderiza ilustración SVG, título, descripción y CTA opcional', async () => {
    const wrapper = mount(EmptyStateCard, {
      props: {
        title: 'Sin pendientes',
        description: 'No hay incidencias abiertas en el condominio.',
        actionLabel: 'Reportar nueva',
        icon: 'check',
      },
    });

    expect(wrapper.find('svg').attributes('aria-hidden')).toBe('true');
    expect(wrapper.text()).toContain('Sin pendientes');
    expect(wrapper.text()).toContain('No hay incidencias abiertas en el condominio.');

    const cta = wrapper.find('.empty-state-card__cta');
    expect(cta.exists()).toBe(true);
    await cta.trigger('click');
    expect(wrapper.emitted('action')).toHaveLength(1);

    const minimal = mount(EmptyStateCard, {
      props: {
        title: 'Vacío',
        description: 'Sin registros.',
      },
    });
    expect(minimal.find('.empty-state-card__cta').exists()).toBe(false);
  });
});
