import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import AmenitiesReservationView from './AmenitiesReservationView.vue';
import { useAccessAmenitiesStore } from '../../stores/accessAmenitiesStore';
import { useAuthStore } from '../../stores/authStore';
import { useOperationsStore } from '../../stores/operationsStore';

describe('AmenitiesReservationView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('configura área social, solicita reserva con solvencia e inspecciona post-evento sin PKs', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 1,
      nombre: 'Presidente',
      cedula: 'V-1',
      correo: 'pres@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PRESIDENTE',
      unidad_activa_id: 2,
    });

    const opsStore = useOperationsStore();
    const unidadesList = [
      { id: 1, identificador: 'PB-01', estructura_id: 1 },
      { id: 2, identificador: 'PB-02', estructura_id: 1 },
    ];
    opsStore.data.unidades = unidadesList;
    vi.spyOn(opsStore, 'fetchUnidades').mockResolvedValue(unidadesList);

    const store = useAccessAmenitiesStore();
    const areasSpy = vi.spyOn(store, 'fetchAreasSociales').mockResolvedValue([]);
    vi.spyOn(store, 'fetchReservas').mockResolvedValue([]);
    vi.spyOn(store, 'crearAreaSocial').mockImplementation(async (payload) => {
      const area = {
        id: 7,
        nombre: payload.nombre,
        aforo_maximo: payload.aforo_maximo,
        costo_uso_usd: payload.costo_uso_usd,
        deposito_garantia_usd: payload.deposito_garantia_usd,
        requiere_solvencia_estricta: payload.requiere_solvencia_estricta,
        es_activa: true,
      };
      store.areasSociales = [area];
      return area;
    });
    vi.spyOn(store, 'solicitarReservaArea').mockImplementation(async (payload) => {
      const reserva = {
        id: 30,
        area_id: payload.area_id,
        nombre_area: 'Salón de Fiestas Principal',
        unidad_id: payload.unidad_id,
        identificador_unidad: 'PB-02',
        solicitante_id: 1,
        fecha_evento: payload.fecha_evento,
        motivo_evento: payload.motivo_evento,
        estado: 'CONFIRMADA' as const,
        tarea_inspeccion_id: 105,
        observaciones_inspeccion: null,
        creado_en: '2026-10-30T10:00:00Z',
      };
      store.reservas = [reserva];
      return reserva;
    });
    vi.spyOn(store, 'inspeccionarReserva').mockImplementation(async (_id, payload) => {
      store.reservas[0].estado = payload.estado;
      store.reservas[0].observaciones_inspeccion = payload.observaciones_inspeccion;
      return store.reservas[0];
    });

    const wrapper = mount(AmenitiesReservationView);
    await flushPromises();

    expect(wrapper.find('#solvency-gate-banner').exists()).toBe(true);
    expect(wrapper.find('#amenities-empty-state').exists()).toBe(true);
    expect(wrapper.find('#reservations-empty-state').exists()).toBe(true);
    expect(wrapper.find('#input-reserva-unidad').text()).toContain('PB-02');

    // Envíos vacíos no disparan peticiones
    await wrapper.find('#form-crear-area').trigger('submit.prevent');
    expect(store.crearAreaSocial).not.toHaveBeenCalled();

    await wrapper.find('#form-solicitar-reserva').trigger('submit.prevent');
    expect(store.solicitarReservaArea).not.toHaveBeenCalled();

    // 1. Crear Área Social
    await wrapper.find('#input-area-nombre').setValue('Salón de Fiestas Principal');
    await wrapper.find('#input-area-aforo').setValue('80');
    await wrapper.find('#input-area-costo').setValue('35.00');
    await wrapper.find('#input-area-deposito').setValue('100.00');
    await wrapper.find('#form-crear-area').trigger('submit.prevent');
    await flushPromises();

    expect(store.crearAreaSocial).toHaveBeenCalled();
    expect(wrapper.findAll('.amenity-card')).toHaveLength(1);
    expect(wrapper.find('#amenities-success-banner').text()).toContain(
      'Salón de Fiestas Principal',
    );

    // 2. Solicitar Reserva
    await wrapper.find('#input-reserva-unidad').setValue('2');
    await wrapper.find('#input-reserva-fecha').setValue('2026-12-22');
    await wrapper.find('#input-reserva-motivo').setValue('Cumpleaños familiar infantil');
    await wrapper.find('#form-solicitar-reserva').trigger('submit.prevent');
    await flushPromises();

    expect(store.solicitarReservaArea).toHaveBeenCalled();
    expect(wrapper.find('#amenities-success-banner').text()).not.toContain('Reserva #30');
    expect(wrapper.find('#amenities-success-banner').text()).not.toContain('#105');
    expect(wrapper.findAll('.reservation-card')).toHaveLength(1);
    expect(wrapper.find('#btn-inspect-ok-30').exists()).toBe(true);

    // 3. Inspección Post-Evento OK
    await wrapper.find('#btn-inspect-ok-30').trigger('click');
    await flushPromises();

    expect(store.inspeccionarReserva).toHaveBeenCalledWith(
      30,
      expect.objectContaining({ estado: 'FINALIZADA_SIN_DANOS' }),
    );
    expect(wrapper.find('#btn-inspect-ok-30').exists()).toBe(false);

    await wrapper.find('#btn-dual-refresh').trigger('click');
    await flushPromises();
    expect(areasSpy).toHaveBeenCalledTimes(2);
  });

  it('muestra banner de error ante rechazo por morosidad, soporta reporte con daños y oculta gestión a residente', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 3,
      nombre: 'Tesorero',
      cedula: 'V-3',
      correo: 'tes@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'TESORERO',
      unidad_activa_id: 3,
    });

    const opsStore = useOperationsStore();
    vi.spyOn(opsStore, 'fetchUnidades').mockResolvedValue([]);
    const store = useAccessAmenitiesStore();
    vi.spyOn(store, 'fetchAreasSociales').mockImplementation(async () => {
      const area = {
        id: 2,
        nombre: 'Parrillera',
        aforo_maximo: 20,
        costo_uso_usd: '15.00',
        deposito_garantia_usd: '50.00',
        requiere_solvencia_estricta: false,
        es_activa: true,
      };
      store.areasSociales = [area];
      return [area];
    });
    vi.spyOn(store, 'fetchReservas').mockImplementation(async () => {
      const res = {
        id: 40,
        area_id: 2,
        nombre_area: 'Parrillera',
        unidad_id: 3,
        identificador_unidad: '1-B',
        solicitante_id: 3,
        fecha_evento: '2026-12-28',
        motivo_evento: 'Parrillada',
        estado: 'CONFIRMADA' as const,
        tarea_inspeccion_id: null,
        observaciones_inspeccion: null,
        creado_en: '2026-10-30T10:00:00Z',
      };
      store.reservas = [res];
      return [res];
    });
    vi.spyOn(store, 'solicitarReservaArea').mockImplementation(async () => {
      store.error = 'Reserva bloqueada por morosidad: La unidad solicitante registra deuda';
      throw new Error(store.error);
    });
    vi.spyOn(store, 'inspeccionarReserva').mockImplementation(async (_id, payload) => {
      store.reservas[0].estado = payload.estado;
      store.reservas[0].observaciones_inspeccion = payload.observaciones_inspeccion;
      return store.reservas[0];
    });

    const wrapper = mount(AmenitiesReservationView);
    await flushPromises();

    await wrapper.find('#input-reserva-motivo').setValue('Reunión vecinal');
    await wrapper.find('#form-solicitar-reserva').trigger('submit.prevent');
    await flushPromises();

    expect(wrapper.find('#amenities-error-banner').text()).toContain(
      'Reserva bloqueada por morosidad',
    );

    await wrapper.find('#btn-inspect-damage-40').trigger('click');
    await flushPromises();

    expect(store.inspeccionarReserva).toHaveBeenCalledWith(
      40,
      expect.objectContaining({ estado: 'FINALIZADA_CON_DANOS' }),
    );

    // Propietario no ve creación de áreas ni botones de inspección
    authStore.setProfileForTesting({
      id: 99,
      nombre: 'Residente',
      cedula: 'V-99',
      correo: 'res@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });
    await flushPromises();
    expect(wrapper.find('#form-crear-area').exists()).toBe(false);
    expect(wrapper.find('#btn-inspect-ok-40').exists()).toBe(false);
  });

  it('permite cancelar una reserva confirmada y muestra error si falla la cancelación', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 3,
      nombre: 'Solicitante',
      cedula: 'V-3',
      correo: 'sol@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });

    const opsStore = useOperationsStore();
    vi.spyOn(opsStore, 'fetchUnidades').mockResolvedValue([]);
    const store = useAccessAmenitiesStore();
    vi.spyOn(store, 'fetchAreasSociales').mockResolvedValue([]);
    vi.spyOn(store, 'fetchReservas').mockImplementation(async () => {
      const res = {
        id: 51,
        area_id: 2,
        nombre_area: 'Salón',
        unidad_id: 3,
        identificador_unidad: '1-B',
        solicitante_id: 3,
        fecha_evento: '2026-12-30',
        motivo_evento: 'Brindis',
        estado: 'CONFIRMADA' as const,
        tarea_inspeccion_id: 88,
        observaciones_inspeccion: null,
        creado_en: '2026-10-30T10:00:00Z',
      };
      store.reservas = [res];
      return [res];
    });
    vi.spyOn(store, 'cancelarReserva')
      .mockImplementationOnce(async () => {
        store.error = 'Solo reservas confirmadas pueden cancelarse';
        throw new Error(store.error);
      })
      .mockImplementationOnce(async () => {
        store.reservas[0].estado = 'CANCELADA';
        return store.reservas[0];
      });

    const wrapper = mount(AmenitiesReservationView);
    await flushPromises();

    await wrapper.find('#btn-cancelar-reserva-51').trigger('click');
    await flushPromises();
    expect(wrapper.find('#amenities-error-banner').text()).toContain(
      'Solo reservas confirmadas pueden cancelarse',
    );

    await wrapper.find('#btn-cancelar-reserva-51').trigger('click');
    await flushPromises();
    expect(store.cancelarReserva).toHaveBeenCalledWith(51);
    expect(wrapper.find('.badge--cancelada').exists()).toBe(true);
    expect(wrapper.find('#btn-cancelar-reserva-51').exists()).toBe(false);
  });

  it('valida rangos de aforo y montos USD en creación de áreas sociales y manejo de errores', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 1,
      nombre: 'Presidente',
      cedula: 'V-1',
      correo: 'pres@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PRESIDENTE',
    });

    const opsStore = useOperationsStore();
    vi.spyOn(opsStore, 'fetchUnidades').mockResolvedValue([]);
    const store = useAccessAmenitiesStore();
    vi.spyOn(store, 'fetchAreasSociales').mockResolvedValue([]);
    vi.spyOn(store, 'fetchReservas').mockResolvedValue([]);
    vi.spyOn(store, 'crearAreaSocial').mockImplementation(async () => {
      store.error = 'El área ya existe';
      throw new Error(store.error);
    });

    const wrapper = mount(AmenitiesReservationView);
    await flushPromises();

    // Aforo fuera de rango 1..500
    await wrapper.find('#input-area-nombre').setValue('Salón Sur');
    await wrapper.find('#input-area-aforo').setValue('0');
    await wrapper.find('#form-crear-area').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('.alert--error').text()).toContain('entre 1 y 500');

    // Costo o depósito inválidos
    await wrapper.find('#input-area-aforo').setValue('40');
    await wrapper.find('#input-area-costo').setValue('-5');
    await wrapper.find('#form-crear-area').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('.alert--error').text()).toContain('montos USD válidos');

    // Error del backend al crear área y cambio en selector de área
    await wrapper.find('#input-area-costo').setValue('20.00');
    await wrapper.find('#input-area-deposito').setValue('30.00');
    await wrapper.find('#select-reserva-area').setValue('1');
    await wrapper.find('#form-crear-area').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('#amenities-error-banner').text()).toContain('El área ya existe');
  });
});
