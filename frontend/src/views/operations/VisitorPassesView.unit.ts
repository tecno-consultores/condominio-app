import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import VisitorPassesView from './VisitorPassesView.vue';
import { useAccessAmenitiesStore } from '../../stores/accessAmenitiesStore';
import { useAuthStore } from '../../stores/authStore';
import { useOperationsStore } from '../../stores/operationsStore';

describe('VisitorPassesView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('emite un pase QR firmado, permite copiar el token y revocar pases activos sin exponer JTI', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 2,
      nombre: 'Residente',
      cedula: 'V-2',
      correo: 'res@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
      unidad_activa_id: 1,
    });

    const opsStore = useOperationsStore();
    const unidadesList = [{ id: 1, identificador: 'PB-01', estructura_id: 1 }];
    opsStore.data.unidades = unidadesList;
    vi.spyOn(opsStore, 'fetchUnidades').mockResolvedValue(unidadesList);

    const store = useAccessAmenitiesStore();
    const fetchSpy = vi.spyOn(store, 'fetchMisPases').mockResolvedValue([]);
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
    expect(wrapper.find('#input-pase-unidad').text()).toContain('PB-01');

    // Intento con campos vacíos no dispara crearPaseVisita
    await wrapper.find('#form-crear-pase-qr').trigger('submit.prevent');
    expect(store.crearPaseVisita).not.toHaveBeenCalled();

    await wrapper.find('#input-pase-unidad').setValue('1');
    await wrapper.find('#select-pase-modalidad').setValue('UNICO_USO');
    await wrapper.find('#input-pase-horas').setValue('12');
    await wrapper.find('#input-pase-nombre').setValue('Carlos Mendoza');
    await wrapper.find('#input-pase-cedula').setValue('V-19888777');
    await wrapper.find('#input-pase-placa').setValue('AB123CD');
    await wrapper.find('#form-crear-pase-qr').trigger('submit.prevent');
    await flushPromises();

    expect(store.crearPaseVisita).toHaveBeenCalled();
    expect(wrapper.find('#passes-success-banner').text()).toContain('Carlos Mendoza');
    expect(wrapper.find('#passes-success-banner').text()).not.toContain('JTI:');
    expect(wrapper.find('#qr-pass-card-10').exists()).toBe(true);

    await wrapper.find('#btn-copy-qr-10').trigger('click');
    await flushPromises();
    expect(writeTextMock).toHaveBeenCalledWith('b64claims.hmacsig');
    expect(wrapper.find('#btn-copy-qr-10').text()).toBe('Token Copiado');

    await wrapper.find('#btn-revoke-qr-10').trigger('click');
    await flushPromises();
    expect(store.revocarPaseVisita).toHaveBeenCalledWith(10);
    expect(wrapper.find('#passes-success-banner').text()).toContain('Pase de visita revocado');
    expect(wrapper.find('#passes-success-banner').text()).not.toContain('Pase #10');

    await wrapper.find('#btn-dual-refresh').trigger('click');
    await flushPromises();
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it('muestra banner de error cuando el store reporta un fallo', async () => {
    const opsStore = useOperationsStore();
    vi.spyOn(opsStore, 'fetchUnidades').mockResolvedValue([]);
    const store = useAccessAmenitiesStore();
    vi.spyOn(store, 'fetchMisPases').mockImplementation(async () => {
      store.error = 'No posee contrato activo en la unidad';
      return [];
    });

    const wrapper = mount(VisitorPassesView);
    await flushPromises();

    expect(wrapper.find('#passes-error-banner').text()).toContain('No posee contrato activo');
  });

  it('selecciona primera unidad si activeUnitId es null y valida horas de vigencia 1-72', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 1,
      nombre: 'Presidente',
      cedula: 'V-1',
      correo: 'pres@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PRESIDENTE',
      unidad_activa_id: null,
    });
    const opsStore = useOperationsStore();
    vi.spyOn(opsStore, 'fetchUnidades').mockImplementation(async () => {
      opsStore.data.unidades = [{ id: 9, identificador: 'PH-1', estructura_id: 1 }];
      return opsStore.data.unidades;
    });
    const store = useAccessAmenitiesStore();
    vi.spyOn(store, 'fetchMisPases').mockResolvedValue([]);
    vi.spyOn(store, 'crearPaseVisita').mockRejectedValue(new Error('No debe enviarse'));

    const wrapper = mount(VisitorPassesView);
    await flushPromises();

    expect((wrapper.find('#input-pase-unidad').element as HTMLSelectElement).value).toBe('9');
    await wrapper.find('#input-pase-nombre').setValue('Visitante');
    await wrapper.find('#input-pase-cedula').setValue('V-10200300');
    await wrapper.find('#input-pase-horas').setValue('0');
    await wrapper.find('#form-crear-pase-qr').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('.alert--error').text()).toContain('entre 1 y 72 horas');

    await wrapper.find('#input-pase-horas').setValue('80');
    await wrapper.find('#form-crear-pase-qr').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('.alert--error').text()).toContain('entre 1 y 72 horas');
  });
});
