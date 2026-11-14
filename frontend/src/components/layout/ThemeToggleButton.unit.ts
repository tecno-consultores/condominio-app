// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { beforeEach, describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import ThemeToggleButton from './ThemeToggleButton.vue';
import { resetThemeListenersForTests } from '../../composables/useThemeMode';

describe('ThemeToggleButton.vue', () => {
  beforeEach(() => {
    window.localStorage?.clear?.();
    document.head.innerHTML = '';
    document.documentElement.className = '';
    resetThemeListenersForTests();
  });

  it('alterna entre modo claro y oscuro actualizando aria-pressed, etiquetas y el DOM raíz', async () => {
    const wrapper = mount(ThemeToggleButton);
    const btn = wrapper.find('#btn-theme-toggle');

    expect(btn.exists()).toBe(true);
    expect(btn.attributes('aria-pressed')).toBe('false');
    expect(btn.attributes('aria-label')).toBe('Cambiar a modo oscuro');
    expect(btn.text()).toContain('Modo oscuro');

    await btn.trigger('click');
    expect(btn.attributes('aria-pressed')).toBe('true');
    expect(btn.attributes('aria-label')).toBe('Cambiar a modo claro');
    expect(btn.text()).toContain('Modo claro');
    expect(document.documentElement.classList.contains('theme-dark')).toBe(true);

    const compactWrapper = mount(ThemeToggleButton, {
      props: { buttonId: 'btn-sidebar-theme-toggle', compact: true },
    });
    expect(compactWrapper.find('#btn-sidebar-theme-toggle').text()).toBe('');
  });
});
