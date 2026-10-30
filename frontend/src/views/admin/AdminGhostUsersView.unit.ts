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

  it('lista usuarios fantasma pendientes y permite vincularlos y activar su cuenta', async () => {
    const store = useOperationsStore();
    vi.spyOn(store, 'fetchAdminData').mockResolvedValue();
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
      rol: 'VOCERO',
    });

    const wrapper = mount(AdminGhostUsersView);
    await flushPromises();

    await wrapper.find('#select-unit-18').setValue('2');
    await wrapper.find('#select-ocupante-18').setValue('INQUILINO');
    await wrapper.find('#select-rol-18').setValue('VOCERO');
    await wrapper.find('#btn-activate-user-18').trigger('click');
    await flushPromises();

    expect(assignSpy).toHaveBeenCalledWith(18, {
      unidad_id: 2,
      tipo_ocupante: 'INQUILINO',
      rol: 'VOCERO',
    });
    expect(wrapper.find('#ghost-success-banner').text()).toContain('Sofía Rojas');
  });

  it('muestra estado vacío, banner de caché y maneja error en asignación', async () => {
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
    vi.spyOn(store, 'asignarUsuarioFantasma').mockRejectedValue(new Error('Fallo red'));
    await flushPromises();
    await wrapper.find('#btn-activate-user-19').trigger('click');
    await flushPromises();
    expect(wrapper.find('#ghost-success-banner').exists()).toBe(false);
  });
});
