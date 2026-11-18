import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import AdminBoardRolesView from './AdminBoardRolesView.vue';
import { useOperationsStore } from '../../stores/operationsStore';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/admin/junta' }),
}));

describe('AdminBoardRolesView.vue — Gestión de Cargos de Junta', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('valida identificador de propietario y permite asignar un cargo de Junta de Condominio', async () => {
    const store = useOperationsStore();
    const roleSpy = vi.spyOn(store, 'asignarCargoJunta').mockResolvedValue({
      id: 14,
      nombre: 'Roberto Gómez',
      cedula: 'V-14000999',
      correo: 'roberto@test.com',
      telefono: '0414-9999999',
      es_activo: true,
      rol: 'TESORERO',
    });

    const wrapper = mount(AdminBoardRolesView);

    await wrapper.find('#form-asignar-junta').trigger('submit.prevent');
    expect(wrapper.find('#junta-validation-error').exists()).toBe(true);

    await wrapper.find('#input-junta-usuario-id').setValue('14');
    await wrapper.find('#select-junta-cargo').setValue('TESORERO');
    await wrapper.find('#form-asignar-junta').trigger('submit.prevent');
    await flushPromises();

    expect(roleSpy).toHaveBeenCalledWith({
      usuario_id: 14,
      cargo: 'TESORERO',
    });
    expect(wrapper.find('#junta-success-banner').text()).toContain('Roberto Gómez');
    expect(wrapper.find('#junta-success-banner').text()).not.toContain('#14');
  });

  it('muestra alerta cuando asignarCargoJunta falla y nunca inquilinos en directiva', async () => {
    const store = useOperationsStore();
    vi.spyOn(store, 'asignarCargoJunta').mockImplementation(async () => {
      store.isStale = false;
      store.errorMessage = 'El usuario no posee una propiedad activa';
      throw new Error('400');
    });

    const wrapper = mount(AdminBoardRolesView);
    expect(wrapper.find('#select-junta-cargo').text()).not.toContain('INQUILINO');

    await wrapper.find('#input-junta-usuario-id').setValue('29');
    await wrapper.find('#form-asignar-junta').trigger('submit.prevent');
    await flushPromises();

    expect(wrapper.find('#junta-error-banner').text()).toContain('propiedad activa');
  });
});
