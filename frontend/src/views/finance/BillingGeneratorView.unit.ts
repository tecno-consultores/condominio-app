import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BillingGeneratorView from './BillingGeneratorView.vue';
import { useFinanceStore } from '../../stores/financeStore';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/tesoreria/facturacion' }),
}));

describe('BillingGeneratorView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('valida campos, emite facturación trimodal, crea fondos y abre el modal de desglose', async () => {
    const store = useFinanceStore();
    vi.spyOn(store, 'fetchDashboardData').mockResolvedValue();
    vi.spyOn(store, 'fetchFondos').mockResolvedValue();
    const facturarSpy = vi.spyOn(store, 'facturarPeriodo').mockResolvedValue({
      periodo: '2026-10',
      modalidad: 'CUOTA_FIJA',
      recibos_emitidos: 4,
      total_egresos_comunes_usd: '60.00',
      recargo_fondo_reserva_usd: '0.00',
      cuota_extraordinaria_total_usd: '0.00',
      total_facturado_bruto_usd: '100.00',
      total_credito_descontado_usd: '0.00',
      total_facturado_neto_usd: '100.00',
      superavit_conciliado_fondo_usd: '40.00',
    });
    const crearFondoSpy = vi.spyOn(store, 'crearFondo').mockResolvedValue({
      id: 1,
      nombre: 'Fondo de Reserva Legal',
      tipo: 'RESERVA_LEGAL',
      porcentaje_recargo: '10.00',
      saldo_actual_usd: '0.00',
      es_activo: true,
    });
    const desgloseSpy = vi.spyOn(store, 'fetchReciboDesglose').mockImplementation(async () => {
      store.data.desgloseActivo = {
        recibo_id: 1,
        unidad_id: 1,
        identificador_unidad: 'Apto 1-A',
        alicuota_aplicada: '25.0000',
        periodo: '2026-10',
        monto_usd: '25.00',
        monto_pagado_usd: '0.00',
        saldo_pendiente_usd: '25.00',
        credito_descontado_usd: '0.00',
        estado: 'PENDIENTE',
        bloqueado: false,
        items: [],
      };
      return store.data.desgloseActivo;
    });

    store.data.resumen = {
      deuda_total_usd: '25.00',
      total_egresos_usd: '60.00',
      gastos_por_categoria: {},
      estado_cobranza: [
        {
          recibo_id: 1,
          unidad_id: 1,
          periodo: '2026-10',
          estado: 'PENDIENTE',
          saldo_usd: '25.00',
        },
      ],
    };

    const wrapper = mount(BillingGeneratorView);
    await flushPromises();

    // Validación de periodo inválido
    await wrapper.find('#input-facturar-periodo').setValue('invalido');
    await wrapper.find('#form-facturar-periodo').trigger('submit.prevent');
    expect(wrapper.find('#billing-validation-error').text()).toContain('YYYY-MM');

    // Validación de cuota fija <= 0
    await wrapper.find('#input-facturar-periodo').setValue('2026-10');
    await wrapper.find('#select-facturar-modalidad').setValue('CUOTA_FIJA');
    await wrapper.find('#input-monto-cuota-fija').setValue('0');
    await wrapper.find('#form-facturar-periodo').trigger('submit.prevent');
    expect(wrapper.find('#billing-validation-error').text()).toContain('cuota fija mensual');

    // Emisión exitosa en CUOTA_FIJA
    await wrapper.find('#input-monto-cuota-fija').setValue('25.00');
    await wrapper.find('#check-incluir-reserva').setValue(false);
    await wrapper.find('#input-cuota-extra-monto').setValue('15.00');
    await wrapper.find('#input-cuota-extra-desc').setValue('Bomba de agua');
    await wrapper.find('#form-facturar-periodo').trigger('submit.prevent');
    await flushPromises();
    expect(facturarSpy).toHaveBeenCalledOnce();
    expect(wrapper.find('#billing-success-banner').text()).toContain('Facturación 2026-10');

    // Emisión en modalidad ALICUOTA
    await wrapper.find('#select-facturar-modalidad').setValue('ALICUOTA');
    await wrapper.find('#input-cuota-extra-monto').setValue('');
    await wrapper.find('#input-cuota-extra-desc').setValue('');
    await wrapper.find('#form-facturar-periodo').trigger('submit.prevent');
    await flushPromises();

    // Validación y creación de Fondo
    await wrapper.find('#input-fondo-nombre').setValue('AB');
    await wrapper.find('#form-crear-fondo').trigger('submit.prevent');
    expect(wrapper.find('#billing-validation-error').text()).toContain('3 caracteres');

    await wrapper.find('#input-fondo-nombre').setValue('Fondo de Reserva Legal');
    await wrapper.find('#select-fondo-tipo').setValue('CAJA_CHICA');
    await wrapper.find('#input-fondo-porcentaje').setValue('5.00');
    await wrapper.find('#form-crear-fondo').trigger('submit.prevent');
    await flushPromises();
    expect(crearFondoSpy).toHaveBeenCalledOnce();

    // Inspeccionar y cerrar desglose de recibo
    await wrapper.find('#btn-inspect-recibo-1').trigger('click');
    await flushPromises();
    expect(desgloseSpy).toHaveBeenCalledWith(1);
    expect(wrapper.find('#modal-recibo-desglose').exists()).toBe(true);
    await wrapper.find('#btn-close-desglose').trigger('click');
    expect(wrapper.find('#modal-recibo-desglose').exists()).toBe(false);

    // Manejo de errores y banner de error del store
    store.errorMessage = 'Error de facturación simulado';
    facturarSpy.mockRejectedValueOnce(new Error('Fallo red'));
    crearFondoSpy.mockRejectedValueOnce(new Error('Fallo red'));
    desgloseSpy.mockRejectedValueOnce(new Error('Fallo red'));
    await wrapper.find('#form-facturar-periodo').trigger('submit.prevent');
    await wrapper.find('#input-fondo-nombre').setValue('Fondo Contingencia');
    await wrapper.find('#form-crear-fondo').trigger('submit.prevent');
    await wrapper.find('#btn-inspect-recibo-1').trigger('click');
    await flushPromises();
    expect(wrapper.find('#billing-error-banner').exists()).toBe(true);
  });
});
