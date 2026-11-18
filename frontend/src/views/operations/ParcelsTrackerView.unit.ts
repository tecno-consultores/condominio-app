import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import ParcelsTrackerView from './ParcelsTrackerView.vue';
import { useAccessAmenitiesStore } from '../../stores/accessAmenitiesStore';
import { useAuthStore } from '../../stores/authStore';
import { useOperationsStore } from '../../stores/operationsStore';

describe('ParcelsTrackerView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('registra paquete en garita como CONSERJE, oculta formulario a residente y confirma retiro', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 5,
      nombre: 'Conserje',
      cedula: 'V-5',
      correo: 'conserje@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'CONSERJE',
    });

    const opsStore = useOperationsStore();
    const unidadesList = [{ id: 1, identificador: '2-B', estructura_id: 1 }];
    opsStore.data.unidades = unidadesList;
    vi.spyOn(opsStore, 'fetchUnidades').mockResolvedValue(unidadesList);

    const store = useAccessAmenitiesStore();
    const fetchSpy = vi.spyOn(store, 'fetchPaqueteria').mockResolvedValue([]);
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
    expect(wrapper.find('#input-parcel-unidad').text()).toContain('2-B');

    // Envío sin descripción no dispara registrarPaquete
    await wrapper.find('#form-registrar-paquete').trigger('submit.prevent');
    expect(store.registrarPaquete).not.toHaveBeenCalled();

    await wrapper.find('#input-parcel-unidad').setValue('1');
    await wrapper.find('#select-parcel-empresa').setValue('ZOOM');
    await wrapper.find('#input-parcel-descripcion').setValue('Caja sellada guía #99812');
    await wrapper.find('#input-parcel-foto').setValue('s3://condominio-media/paquetes/foto.avif');
    await wrapper.find('#form-registrar-paquete').trigger('submit.prevent');
    await flushPromises();

    expect(store.registrarPaquete).toHaveBeenCalled();
    expect(wrapper.find('#parcels-success-banner').text()).not.toContain('#25');
    expect(wrapper.findAll('.parcel-card')).toHaveLength(1);
    expect(wrapper.find('#btn-confirm-parcel-25').exists()).toBe(true);

    await wrapper.find('#btn-confirm-parcel-25').trigger('click');
    await flushPromises();

    expect(store.confirmarEntregaPaquete).toHaveBeenCalledWith(25);
    expect(wrapper.find('#parcels-success-banner').text()).toContain('ENTREGADO');
    expect(wrapper.find('#parcels-success-banner').text()).not.toContain('Paquete #25');
    expect(wrapper.find('#btn-confirm-parcel-25').exists()).toBe(false);

    await wrapper.find('#btn-dual-refresh').trigger('click');
    await flushPromises();
    expect(fetchSpy).toHaveBeenCalledTimes(2);

    // Residente no ve formulario de registro en garita
    authStore.setProfileForTesting({
      id: 2,
      nombre: 'Residente',
      cedula: 'V-2',
      correo: 'res@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });
    await flushPromises();
    expect(wrapper.find('#form-registrar-paquete').exists()).toBe(false);
  });

  it('muestra banner de error cuando ocurre un fallo en el store', async () => {
    const opsStore = useOperationsStore();
    vi.spyOn(opsStore, 'fetchUnidades').mockResolvedValue([]);
    const store = useAccessAmenitiesStore();
    vi.spyOn(store, 'fetchPaqueteria').mockImplementation(async () => {
      store.error = 'Error de permisos en paquetería';
      return [];
    });

    const wrapper = mount(ParcelsTrackerView);
    await flushPromises();

    expect(wrapper.find('#parcels-error-banner').text()).toContain('Error de permisos');
  });

  it('permite a PROPIETARIO confirmar retiro de su propia unidad y renderiza evidencia segura https://', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 2,
      nombre: 'Residente Propio',
      cedula: 'V-2',
      correo: 'res@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
      unidad_activa_id: 7,
    });
    const opsStore = useOperationsStore();
    vi.spyOn(opsStore, 'fetchUnidades').mockImplementation(async () => {
      opsStore.data.unidades = [{ id: 7, identificador: '7-C', estructura_id: 1 }];
      return opsStore.data.unidades;
    });

    const store = useAccessAmenitiesStore();
    vi.spyOn(store, 'fetchPaqueteria').mockImplementation(async () => {
      store.paquetes = [
        {
          id: 301,
          unidad_id: 7,
          identificador_unidad: '7-C',
          recibido_por_id: 5,
          empresa_envio: 'TEALCA',
          descripcion: 'Repuesto automotriz',
          url_foto_evidencia: 'https://cdn.condominio.local/paq/301.avif',
          estado: 'EN_GARITA',
          fecha_recepcion: '2026-10-30T10:00:00Z',
          fecha_entrega: null,
          retirado_por_id: null,
        },
        {
          id: 302,
          unidad_id: 8,
          identificador_unidad: '8-D',
          recibido_por_id: 5,
          empresa_envio: 'MRW',
          descripcion: 'Documento ajeno',
          url_foto_evidencia: 's3://condominio-media/paquetes/302.avif',
          estado: 'EN_GARITA',
          fecha_recepcion: '2026-10-30T11:00:00Z',
          fecha_entrega: null,
          retirado_por_id: null,
        },
      ];
      return store.paquetes;
    });
    vi.spyOn(store, 'confirmarEntregaPaquete').mockRejectedValueOnce(new Error('Fallo entrega'));

    const wrapper = mount(ParcelsTrackerView);
    await flushPromises();

    expect(wrapper.find('.parcel-card__image').attributes('src')).toBe(
      'https://cdn.condominio.local/paq/301.avif',
    );
    expect(wrapper.find('.parcel-card__processing').exists()).toBe(true);
    expect(wrapper.find('#btn-confirm-parcel-301').exists()).toBe(true);
    expect(wrapper.find('#btn-confirm-parcel-302').exists()).toBe(false);

    await wrapper.find('#btn-confirm-parcel-301').trigger('click');
    await flushPromises();
  });
});
