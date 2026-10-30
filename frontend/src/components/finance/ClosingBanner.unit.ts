import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ClosingBanner from './ClosingBanner.vue';

describe('ClosingBanner.vue', () => {
  it('muestra el banner preventivo entre los días 1 y 10 del mes', () => {
    const wrapper = mount(ClosingBanner, {
      props: { dayOfMonth: 5, isClosed: false, periodo: '2026-10' },
    });
    expect(wrapper.find('#closing-banner').exists()).toBe(true);
    expect(wrapper.text()).toContain('Ventana de Cierre Mensual (2026-10)');
  });

  it('muestra alerta de Candado Contable cuando el periodo está cerrado aunque sea día > 10', () => {
    const wrapper = mount(ClosingBanner, {
      props: { dayOfMonth: 22, isClosed: true, periodo: '2026-10' },
    });
    expect(wrapper.find('#closing-banner').classes()).toContain('closing-banner--locked');
    expect(wrapper.text()).toContain('Candado Contable Activo (2026-10)');
  });

  it('oculta el banner fuera de los días 1..10 cuando el mes sigue abierto', () => {
    const wrapper = mount(ClosingBanner, {
      props: { dayOfMonth: 18, isClosed: false },
    });
    expect(wrapper.find('#closing-banner').exists()).toBe(false);
  });
});
