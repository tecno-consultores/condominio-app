import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import CollectionTrafficLight from './CollectionTrafficLight.vue';

describe('CollectionTrafficLight.vue', () => {
  it('muestra mensaje vacío cuando no hay recibos emitidos', () => {
    const wrapper = mount(CollectionTrafficLight, {
      props: { items: [], rateUsdVes: '36.50' },
    });
    expect(wrapper.text()).toContain('No existen recibos emitidos');
  });

  it('ordena la unidad propia primero y calcula el equivalente en VES', () => {
    const wrapper = mount(CollectionTrafficLight, {
      props: {
        rateUsdVes: '40.00',
        ownUnitId: 5,
        items: [
          { unidad_id: 2, periodo: '2026-10', estado: 'SOLVENTE', saldo_usd: '0.00' },
          { unidad_id: 5, periodo: '2026-10', estado: 'ABONO_PARCIAL', saldo_usd: '25.00' },
          { unidad_id: 1, periodo: '2026-10', estado: 'MOROSO', saldo_usd: '75.00' },
        ],
      },
    });

    const rows = wrapper.findAll('.collection-row');
    expect(rows).toHaveLength(3);
    expect(rows[0]?.text()).toContain('Unidad #5');
    expect(rows[0]?.text()).toContain('(Tu unidad)');
    expect(rows[0]?.text()).toContain('1000.00 VES');
    expect(rows[1]?.text()).toContain('Unidad #1');
    expect(rows[2]?.text()).toContain('Unidad #2');
  });
});
