import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import GatehouseScannerView from './GatehouseScannerView.vue';
import { useAccessAmenitiesStore } from '../../stores/accessAmenitiesStore';

describe('GatehouseScannerView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('verifica un pase QR válido en garita y muestra alerta en intento de Replay Attack', async () => {
    const store = useAccessAmenitiesStore();
    vi.spyOn(store, 'verificarPaseQR').mockImplementation(async (token) => {
      if (token === 'replay.token') {
        store.error = 'Alerta de Seguridad: Este pase QR de único uso ya fue utilizado';
        throw new Error(store.error);
      }
      store.error = null;
      const res = {
        autorizado: true,
        pase_id: 50,
        jti: '550e8400-e29b-41d4-a716-446655440111',
        unidad_id: 1,
        identificador_unidad: 'PH-1',
        nombre_visitante: 'Técnico Fibra',
        cedula_visitante: 'V-15000111',
        placa_vehiculo: 'XYZ-999',
        modalidad: 'UNICO_USO' as const,
        estado: 'USADO' as const,
        usado_en: '2026-10-30T12:00:00Z',
        verificado_por_id: 5,
        mensaje: 'Acceso autorizado a Unidad PH-1 para Técnico Fibra.',
      };
      store.ultimoEscaneo = res;
      return res;
    });

    const wrapper = mount(GatehouseScannerView);

    // Envío vacío no invoca al store
    await wrapper.find('#form-verificar-qr-garita').trigger('submit.prevent');
    expect(store.verificarPaseQR).not.toHaveBeenCalled();

    // 1. Primer escaneo válido
    await wrapper.find('#input-scan-qr-token').setValue('valid.token');
    await wrapper.find('#form-verificar-qr-garita').trigger('submit.prevent');
    await flushPromises();

    expect(wrapper.find('#qr-scan-success-card').exists()).toBe(true);
    expect(wrapper.find('#qr-scan-success-card').text()).toContain('Técnico Fibra');
    expect(wrapper.find('#qr-scan-success-card').text()).toContain('XYZ-999');

    // 2. Intento de Replay Attack
    await wrapper.find('#input-scan-qr-token').setValue('replay.token');
    await wrapper.find('#form-verificar-qr-garita').trigger('submit.prevent');
    await flushPromises();

    expect(wrapper.find('#qr-scan-error-alert').exists()).toBe(true);
    expect(wrapper.find('#qr-scan-error-alert').text()).toContain('único uso ya fue utilizado');
  });
});
