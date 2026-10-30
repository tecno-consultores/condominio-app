import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../../services/apiClient';
import TreasuryClosingView from './TreasuryClosingView.vue';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/tesoreria/cierre' }),
}));

describe('TreasuryClosingView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('permite guardar tasa BCV, registrar egreso y activar el Candado Contable con confirmación modal', async () => {
    const postSpy = vi
      .spyOn(apiClient, 'post')
      .mockResolvedValueOnce({ id: 3, fecha: '2026-10-30', tasa_usd_ves: '39.90' })
      .mockResolvedValueOnce({ id: 15, monto_usd: '120.00' })
      .mockResolvedValueOnce({ periodo: '2026-10', estado: 'CERRADO' });

    const wrapper = mount(TreasuryClosingView);

    // 1. Guardar tasa BCV
    await wrapper.find('#input-tasa-bcv').setValue('39.90');
    await wrapper.findAll('form')[0]?.trigger('submit.prevent');
    await flushPromises();
    expect(postSpy).toHaveBeenCalledWith('/api/finanzas/tasa', { tasa_usd_ves: '39.9' });
    expect(wrapper.text()).toContain('39.90 VES/USD');

    // 2. Registrar egreso
    await wrapper.find('#input-egreso-descripcion').setValue('Reparación sello mecánico');
    await wrapper.find('#input-egreso-monto').setValue('120.00');
    await wrapper.findAll('form')[1]?.trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.text()).toContain('Egreso #15 registrado');

    // 3. Candado Contable
    await wrapper.find('#btn-open-closing-modal').trigger('click');
    expect(wrapper.find('#modal-confirm-closing').attributes('open')).toBeDefined();

    await wrapper.find('#btn-confirm-closing').trigger('click');
    await flushPromises();
    expect(postSpy).toHaveBeenCalledWith('/api/finanzas/cierre-mensual', { periodo: '2026-10' });
    expect(wrapper.text()).toContain('Candado Contable activado para el periodo 2026-10');
  });

  it('muestra #closing-conflict-banner cuando el mes ya fue cerrado (HTTP 409)', async () => {
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(409, 'El mes ya fue cerrado (acción inmutable)'),
    );

    const wrapper = mount(TreasuryClosingView);
    await wrapper.find('#btn-open-closing-modal').trigger('click');
    await wrapper.find('#btn-confirm-closing').trigger('click');
    await flushPromises();

    expect(wrapper.find('#closing-conflict-banner').text()).toContain(
      'El mes ya fue cerrado (acción inmutable)',
    );

    // Probar cierre del modal con Cancelar y errores en tasa / egreso
    await wrapper.find('#btn-open-closing-modal').trigger('click');
    await wrapper.find('#btn-cancel-closing').trigger('click');
    expect(wrapper.find('#modal-confirm-closing').attributes('open')).toBeUndefined();

    await wrapper.find('#input-egreso-periodo').setValue('2026-11');
    await wrapper.find('#select-egreso-categoria').setValue('Vigilancia');
    await wrapper.find('#select-egreso-moneda').setValue('VES');

    vi.spyOn(apiClient, 'post')
      .mockRejectedValueOnce(new ApiError(400, 'Tasa inválida'))
      .mockRejectedValueOnce(new ApiError(400, 'Egreso inválido'));

    await wrapper.findAll('form')[0]?.trigger('submit.prevent');
    await flushPromises();
    await wrapper.findAll('form')[1]?.trigger('submit.prevent');
    await flushPromises();
  });
});
