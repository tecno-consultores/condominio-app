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

  it('renderiza categorías con porcentaje y monto en USD', () => {
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
  });
});
