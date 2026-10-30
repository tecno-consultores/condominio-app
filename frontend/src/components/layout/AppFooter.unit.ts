import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import AppFooter from './AppFooter.vue';

describe('AppFooter.vue (In-Flow Ergonomics Anti-JSDOM)', () => {
  it('renderiza el pie de página en el flujo normal del documento con la versión indicada', () => {
    const wrapper = mount(AppFooter, {
      props: { version: '2.1.0' },
    });
    const footer = wrapper.find('#app-inflow-footer');
    expect(footer.exists()).toBe(true);
    expect(footer.text()).toContain('v2.1.0');

    const defaultWrapper = mount(AppFooter);
    expect(defaultWrapper.text()).toContain('v1.0.0');
  });
});
