import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import StaleDataBanner from './StaleDataBanner.vue';

describe('StaleDataBanner.vue', () => {
  it('no renderiza nada cuando isStale es false y muestra el aviso cuando isStale es true', () => {
    const hidden = mount(StaleDataBanner, {
      props: { isStale: false },
    });
    expect(hidden.find('#stale-data-banner').exists()).toBe(false);

    const visible = mount(StaleDataBanner, {
      props: { isStale: true, message: 'Red inestable: mostrando caché local' },
    });
    expect(visible.find('#stale-data-banner').exists()).toBe(true);
    expect(visible.text()).toContain('Red inestable: mostrando caché local');

    const defaultMsg = mount(StaleDataBanner, {
      props: { isStale: true, message: null },
    });
    expect(defaultMsg.text()).toContain('Mostrando los últimos datos sincronizados');
  });
});
