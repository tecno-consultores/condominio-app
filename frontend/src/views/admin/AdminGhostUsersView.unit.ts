import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import AdminGhostUsersView from './AdminGhostUsersView.vue';
import { useOperationsStore } from '../../stores/operationsStore';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/admin/usuarios' }),
}));

describe('AdminGhostUsersView.vue — Bandeja de Usuarios Fantasma Pendientes', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('lista usuarios fantasma pendientes, deshabilita voto asamblea para INQUILINO y activa cuenta', async () => {
    const store = useOperationsStore();
    const fetchSpy = vi.spyOn(store, 'fetchAdminData').mockResolvedValue();
    store.data.unidades = [
      { id: 1, identificador: 'Apto 1-A', estructura_id: 1 },
      { id: 2, identificador: 'Apto 1-B', estructura_id: 1 },
    ];
    store.data.usuariosPendientes = [
      {
        id: 18,
        nombre: 'Sofía Rojas',
        cedula: 'V-18000111',
        correo: 'sofia@test.com',
        telefono: '0414-0001111',
        es_activo: false,
        rol: 'FANTASMA',
      },
    ];
    const assignSpy = vi.spyOn(store, 'asignarUsuarioFantasma').mockResolvedValue({
      id: 18,
      nombre: 'Sofía Rojas',
      cedula: 'V-18000111',
      correo: 'sofia@test.com',
      telefono: '0414-0001111',
      es_activo: true,
      rol: 'INQUILINO',
    });

    const wrapper = mount(AdminGhostUsersView);
    await flushPromises();

    await wrapper.find('#select-unit-18').setValue('2');
    await wrapper.find('#select-ocupante-18').setValue('INQUILINO');
    const voteCheckbox = wrapper.find('#check-votar-18');
    expect((voteCheckbox.element as HTMLInputElement).disabled).toBe(true);
    expect((voteCheckbox.element as HTMLInputElement).checked).toBe(false);

    await wrapper.find('#btn-activate-user-18').trigger('click');
    await flushPromises();

    expect(assignSpy).toHaveBeenCalledWith(18, {
      unidad_id: 2,
      tipo_ocupante: 'INQUILINO',
      rol: 'INQUILINO',
      puede_votar_asamblea: false,
    });
    expect(wrapper.find('#ghost-success-banner').text()).toContain('Sofía Rojas');

    // Cambiar de nuevo a PROPIETARIO habilita voto y rol VOCERO
    await wrapper.find('#select-ocupante-18').setValue('PROPIETARIO');
    expect((voteCheckbox.element as HTMLInputElement).disabled).toBe(false);
    await wrapper.find('#select-rol-18').setValue('VOCERO');
    await wrapper.find('#btn-dual-refresh').trigger('click');
    await flushPromises();
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it('muestra estado vacío, banner de caché/error real y maneja error en asignación', async () => {
    const store = useOperationsStore();
    vi.spyOn(store, 'fetchAdminData').mockResolvedValue();
    store.isStale = true;
    store.errorMessage = 'Caché de usuarios fantasma activa';
    store.data.unidades = [];
    store.data.usuariosPendientes = [];

    const wrapper = mount(AdminGhostUsersView);
    await flushPromises();
    expect(wrapper.find('#ghost-stale-banner').text()).toContain('Caché de usuarios fantasma');
    expect(wrapper.find('#ghost-empty-state').exists()).toBe(true);

    store.data.usuariosPendientes = [
      {
        id: 19,
        nombre: 'Pedro',
        cedula: 'V-19',
        correo: 'p@test.com',
        telefono: '0414',
        es_activo: false,
        rol: 'FANTASMA',
      },
    ];
    vi.spyOn(store, 'asignarUsuarioFantasma').mockImplementation(async () => {
      store.isStale = false;
      store.errorMessage = 'Permiso denegado';
      throw new Error('403');
    });
    await flushPromises();
    await wrapper.find('#btn-activate-user-19').trigger('click');
    await flushPromises();
    expect(wrapper.find('#ghost-error-banner').text()).toContain('Permiso denegado');
    expect(wrapper.find('#ghost-success-banner').exists()).toBe(false);
  });
});
