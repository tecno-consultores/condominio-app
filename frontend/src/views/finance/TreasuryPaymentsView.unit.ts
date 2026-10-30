import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient } from '../../services/apiClient';
import TreasuryPaymentsView from './TreasuryPaymentsView.vue';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/tesoreria/pagos' }),
}));

describe('TreasuryPaymentsView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('lista pagos en revisión y permite aprobar en un toque o rechazar con motivo forense', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce([
      {
        id: 21,
        recibo_id: 1,
        usuario_id: 3,
        monto: '1825.00',
        moneda: 'VES',
        monto_usd: '50.00',
        tasa_cambio: '36.50',
        metodo_pago: 'PAGO_MOVIL',
        numero_referencia: 'REF-21',
        url_comprobante: null,
        estado: 'EN_REVISION',
      },
      {
        id: 22,
        recibo_id: 2,
        usuario_id: 4,
        monto: '30.00',
        moneda: 'USD',
        monto_usd: '30.00',
        tasa_cambio: '36.50',
        metodo_pago: 'ZELLE',
        numero_referencia: null,
        url_comprobante: null,
        estado: 'EN_REVISION',
      },
    ]);

    const putSpy = vi
      .spyOn(apiClient, 'put')
      .mockResolvedValueOnce({ id: 21, estado: 'APROBADO' })
      .mockRejectedValueOnce(new Error('Fallo aprobación'))
      .mockResolvedValueOnce({ id: 22, estado: 'RECHAZADO' });

    const wrapper = mount(TreasuryPaymentsView);
    await flushPromises();

    expect(wrapper.findAll('.payment-card')).toHaveLength(2);
    expect(wrapper.text()).toContain('Efectivo en taquilla');

    // Aprobar primer pago
    await wrapper.find('.btn-approve-payment').trigger('click');
    await flushPromises();
    expect(putSpy).toHaveBeenCalledWith('/api/pagos/21/aprobar', {});
    expect(wrapper.text()).toContain('Pago #21 aprobado');

    // Fallo al aprobar segundo pago -> mantiene tarjeta
    await wrapper.find('.btn-approve-payment').trigger('click');
    await flushPromises();
    expect(wrapper.find('.banner--error').exists()).toBe(true);

    // Abrir modal, cerrarlo y volver a abrir para rechazar segundo pago
    await wrapper.find('.btn-reject-payment').trigger('click');
    await wrapper.find('#btn-cancel-reject').trigger('click');
    await wrapper.find('.btn-reject-payment').trigger('click');
    await wrapper.find('#input-reject-motivo').setValue('Comprobante duplicado de mes anterior');
    await wrapper.find('#modal-reject-reason form').trigger('submit.prevent');
    await flushPromises();

    expect(putSpy).toHaveBeenCalledWith('/api/pagos/22/rechazar', {
      motivo: 'Comprobante duplicado de mes anterior',
    });
    expect(wrapper.text()).toContain('Pago #22 rechazado');
    expect(wrapper.find('.empty-state').exists()).toBe(true);
  });
});
