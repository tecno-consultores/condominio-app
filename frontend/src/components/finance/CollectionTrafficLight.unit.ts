import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import type { EstadoRecibo } from '../../stores/financeStore';
import CollectionTrafficLight from './CollectionTrafficLight.vue';

describe('CollectionTrafficLight.vue', () => {
  it('muestra mensaje vacío cuando no hay recibos emitidos', () => {
    const wrapper = mount(CollectionTrafficLight, {
      props: { items: [], rateUsdVes: '36.50' },
    });
    expect(wrapper.text()).toContain('No existen recibos emitidos');
  });

  it('ordena la unidad propia primero, soporta PAGADO_PARCIAL y tasa BCV ausente sin PKs crudas', () => {
    const wrapper = mount(CollectionTrafficLight, {
      props: {
        rateUsdVes: '40.00',
        ownUnitId: 5,
        unitLabels: { 5: 'Apto 5-A', 1: 'Apto 1-A', 2: 'Apto 2-A' },
        items: [
          { unidad_id: 2, periodo: '2026-10', estado: 'SOLVENTE', saldo_usd: '0.00' },
          { unidad_id: 5, periodo: '2026-10', estado: 'PAGADO_PARCIAL', saldo_usd: '25.00' },
          { unidad_id: 1, periodo: '2026-10', estado: 'MOROSO', saldo_usd: '75.00' },
        ],
      },
    });

    const rows = wrapper.findAll('.collection-row');
    expect(rows).toHaveLength(3);
    expect(rows[0]?.text()).toContain('Apto 5-A');
    expect(rows[0]?.text()).toContain('(Tu unidad)');
    expect(rows[0]?.text()).toContain('1000.00 VES');
    expect(rows[0]?.find('.status-pill--pagado_parcial').exists()).toBe(true);
    expect(rows[0]?.find('.status-pill__glyph').text()).toBe('◐');
    expect(rows[1]?.text()).toContain('Apto 1-A');
    expect(rows[1]?.find('.status-pill__glyph').text()).toBe('✕');
    expect(rows[2]?.text()).toContain('Apto 2-A');
    expect(rows[2]?.find('.status-pill__glyph').text()).toBe('✓');

    const fallbackWrapper = mount(CollectionTrafficLight, {
      props: {
        rateUsdVes: null,
        ownUnitId: 5,
        items: [
          {
            unidad_id: 2,
            periodo: '2026-10',
            estado: 'DESCONOCIDO' as unknown as EstadoRecibo,
            saldo_usd: '10.00',
          },
          { unidad_id: 5, periodo: '2026-10', estado: 'PENDIENTE', saldo_usd: '5.00' },
        ],
      },
    });
    const fallbackRows = fallbackWrapper.findAll('.collection-row');
    expect(fallbackRows[0]?.text()).toContain('Tu inmueble asignado');
    expect(fallbackRows[0]?.text()).toContain('Pendiente tasa BCV');
    expect(fallbackRows[1]?.text()).toContain('Inmueble registrado');
    const glyphs = fallbackWrapper.findAll('.status-pill__glyph').map((g) => g.text());
    expect(glyphs).toEqual(['!', '•']);
  });
});
