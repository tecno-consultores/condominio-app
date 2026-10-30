import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import VisitorPassesView from './VisitorPassesView.vue';
import { useAccessAmenitiesStore } from '../../stores/accessAmenitiesStore';

describe('VisitorPassesView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('emite un pase QR firmado, permite copiar el token y revocar pases activos', async () => {
    const store = useAccessAmenitiesStore();
    vi.spyOn(store, 'fetchMisPases').mockResolvedValue([]);
    vi.spyOn(store, 'crearPaseVisita').mockImplementation(async (payload) => {
      const nuevo = {
        id: 10,
        jti: '550e8400-e29b-41d4-a716-446655440000',
        unidad_id: payload.unidad_id,
        identificador_unidad: 'PB-01',
        creado_por_id: 2,
        nombre_visitante: payload.nombre_visitante,
        cedula_visitante: payload.cedula_visitante,
        placa_vehiculo: payload.placa_vehiculo ?? null,
        modalidad: payload.modalidad,
        valido_desde: '2026-10-30T10:00:00Z',
        valido_hasta: '2026-10-31T10:00:00Z',
        estado: 'ACTIVO' as const,
        usado_en: null,
        verificado_por_id: null,
        firma_hmac: 'f'.repeat(64),
        qr_token: 'b64claims.hmacsig',
      };
      store.pases = [nuevo];
      return nuevo;
    });
    vi.spyOn(store, 'revocarPaseVisita').mockImplementation(async () => {
      store.pases[0].estado = 'REVOCADO';
      return store.pases[0];
    });

    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: { writeText: writeTextMock },
    });

    const wrapper = mount(VisitorPassesView);
    await flushPromises();

    expect(wrapper.find('#passes-empty-state').exists()).toBe(true);

    // Intento con campos vacíos no dispara crearPaseVisita
    await wrapper.find('#form-crear-pase-qr').trigger('submit.prevent');
    expect(store.crearPaseVisita).not.toHaveBeenCalled();

    await wrapper.find('#input-pase-unidad').setValue(1);
    await wrapper.find('#select-pase-modalidad').setValue('UNICO_USO');
    await wrapper.find('#input-pase-horas').setValue(12);
    await wrapper.find('#input-pase-nombre').setValue('Carlos Mendoza');
    await wrapper.find('#input-pase-cedula').setValue('V-19888777');
    await wrapper.find('#input-pase-placa').setValue('AB123CD');
    await wrapper.find('#form-crear-pase-qr').trigger('submit.prevent');
    await flushPromises();

    expect(store.crearPaseVisita).toHaveBeenCalled();
    expect(wrapper.find('#passes-success-banner').text()).toContain('Carlos Mendoza');
    expect(wrapper.find('#qr-pass-card-10').exists()).toBe(true);

    await wrapper.find('#btn-copy-qr-10').trigger('click');
    await flushPromises();
    expect(writeTextMock).toHaveBeenCalledWith('b64claims.hmacsig');
    expect(wrapper.find('#btn-copy-qr-10').text()).toBe('Token Copiado');

    await wrapper.find('#btn-revoke-qr-10').trigger('click');
    await flushPromises();
    expect(store.revocarPaseVisita).toHaveBeenCalledWith(10);
    expect(wrapper.find('#passes-success-banner').text()).toContain('revocado');
  });

  it('muestra banner de error cuando el store reporta un fallo', async () => {
    const store = useAccessAmenitiesStore();
    vi.spyOn(store, 'fetchMisPases').mockImplementation(async () => {
      store.error = 'No posee contrato activo en la unidad';
      return [];
    });

    const wrapper = mount(VisitorPassesView);
    await flushPromises();

    expect(wrapper.find('#passes-error-banner').text()).toContain('No posee contrato activo');
  });
});
