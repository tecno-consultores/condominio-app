import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import ExpensesDonutChart from './ExpensesDonutChart.vue';

describe('ExpensesDonutChart.vue', () => {
  it('muestra mensaje vacío cuando no hay egresos', () => {
    const wrapper = mount(ExpensesDonutChart, {
      props: { expensesByCategory: {}, totalExpensesUsd: '0.00' },
    });
    expect(wrapper.text()).toContain('No se han registrado egresos en el periodo actual.');
  });

  it('renderiza categorías con redondeo ROUND_HALF_UP y stroke-dashoffset acumulado exacto', () => {
    const wrapper = mount(ExpensesDonutChart, {
      props: {
        expensesByCategory: {
          'Bombas de Agua': '300.00',
          Vigilancia: '100.00',
        },
        totalExpensesUsd: '400.00',
      },
    });

    expect(wrapper.text()).toContain('Bombas de Agua');
    expect(wrapper.text()).toContain('300.00 USD (75%)');
    expect(wrapper.text()).toContain('Vigilancia');
    expect(wrapper.text()).toContain('100.00 USD (25%)');

    const circles = wrapper.findAll('svg circle');
    expect(circles).toHaveLength(3);
    expect(circles[1]?.attributes('stroke-dasharray')).toBe('75 25');
    expect(circles[1]?.attributes('stroke-dashoffset')).toBe('25');
    expect(circles[2]?.attributes('stroke-dasharray')).toBe('25 75');
    expect(circles[2]?.attributes('stroke-dashoffset')).toBe('50');
  });
});
