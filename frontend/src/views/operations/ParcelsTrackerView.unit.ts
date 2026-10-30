import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import ParcelsTrackerView from './ParcelsTrackerView.vue';
import { useAccessAmenitiesStore } from '../../stores/accessAmenitiesStore';

describe('ParcelsTrackerView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('registra paquete en garita y permite confirmar su retiro pasando a ENTREGADO', async () => {
    const store = useAccessAmenitiesStore();
    vi.spyOn(store, 'fetchPaqueteria').mockResolvedValue([]);
    vi.spyOn(store, 'registrarPaquete').mockImplementation(async (payload) => {
      const creado = {
        id: 25,
        unidad_id: payload.unidad_id,
        identificador_unidad: '2-B',
        recibido_por_id: 5,
        empresa_envio: payload.empresa_envio,
        descripcion: payload.descripcion,
        url_foto_evidencia: payload.url_foto_evidencia ?? null,
        estado: 'EN_GARITA' as const,
        fecha_recepcion: '2026-10-30T10:00:00Z',
        fecha_entrega: null,
        retirado_por_id: null,
      };
      store.paquetes = [creado];
      return creado;
    });
    vi.spyOn(store, 'confirmarEntregaPaquete').mockImplementation(async () => {
      store.paquetes[0].estado = 'ENTREGADO';
      return store.paquetes[0];
    });

    const wrapper = mount(ParcelsTrackerView);
    await flushPromises();

    expect(wrapper.find('#parcels-empty-state').exists()).toBe(true);

    // Envío sin descripción no dispara registrarPaquete
    await wrapper.find('#form-registrar-paquete').trigger('submit.prevent');
    expect(store.registrarPaquete).not.toHaveBeenCalled();

    await wrapper.find('#input-parcel-unidad').setValue(1);
    await wrapper.find('#select-parcel-empresa').setValue('ZOOM');
    await wrapper.find('#input-parcel-descripcion').setValue('Caja sellada guía #99812');
    await wrapper.find('#input-parcel-foto').setValue('s3://condominio-media/paquetes/foto.avif');
    await wrapper.find('#form-registrar-paquete').trigger('submit.prevent');
    await flushPromises();

    expect(store.registrarPaquete).toHaveBeenCalled();
    expect(wrapper.findAll('.parcel-card')).toHaveLength(1);
    expect(wrapper.find('#btn-confirm-parcel-25').exists()).toBe(true);

    await wrapper.find('#btn-confirm-parcel-25').trigger('click');
    await flushPromises();

    expect(store.confirmarEntregaPaquete).toHaveBeenCalledWith(25);
    expect(wrapper.find('#parcels-success-banner').text()).toContain('ENTREGADO');
    expect(wrapper.find('#btn-confirm-parcel-25').exists()).toBe(false);
  });

  it('muestra banner de error cuando ocurre un fallo en el store', async () => {
    const store = useAccessAmenitiesStore();
    vi.spyOn(store, 'fetchPaqueteria').mockImplementation(async () => {
      store.error = 'Error de permisos en paquetería';
      return [];
    });

    const wrapper = mount(ParcelsTrackerView);
    await flushPromises();

    expect(wrapper.find('#parcels-error-banner').text()).toContain('Error de permisos');
  });
});
