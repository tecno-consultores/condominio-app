import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import App from './App.vue';

describe('App.vue', () => {
  it('monta el contenedor raíz con RouterView', () => {
    const wrapper = mount(App, {
      global: {
        stubs: { RouterView: { template: '<div id="stub-router-view">Vista</div>' } },
      },
    });
    expect(wrapper.find('#condominio-root').exists()).toBe(true);
    expect(wrapper.find('#stub-router-view').text()).toBe('Vista');
  });
});
