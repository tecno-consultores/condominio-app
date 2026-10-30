import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import RegisterView from './RegisterView.vue';
import { useAuthStore } from '../../stores/authStore';
import * as apiClient from '../../services/apiClient';

const pushMock = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}));

describe('RegisterView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pushMock.mockReset();
    vi.restoreAllMocks();
  });

  it('carga unidades al montar, valida campos obligatorios y envía registro idempotente hacia /espera-aprobacion', async () => {
    vi.spyOn(apiClient, 'apiRequest').mockResolvedValueOnce([
      { id: 5, identificador: 'B-202', estructura_id: 1 },
    ]);

    const store = useAuthStore();
    const regSpy = vi.spyOn(store, 'register').mockResolvedValueOnce({
      id: 10,
      nombre: 'Laura Díaz',
      cedula: 'V-20304050',
      correo: 'laura@test.com',
      telefono: '+584140001122',
      es_activo: false,
      rol: 'FANTASMA',
    });

    const wrapper = mount(RegisterView);
    await flushPromises();
    expect(wrapper.find('#reg-unidad').text()).toContain('B-202');

    // Envío vacío -> muestra error
    await wrapper.find('#register-form').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('Complete todos los campos');

    // Completar formulario y enviar
    await wrapper.find('#reg-nombre').setValue('Laura Díaz');
    await wrapper.find('#reg-nombre').trigger('change');
    await wrapper.find('#reg-cedula').setValue('V-20304050');
    await wrapper.find('#reg-correo').setValue('laura@test.com');
    await wrapper.find('#reg-telefono').setValue('+584140001122');
    await wrapper.find('#reg-password').setValue('Password123!');
    await wrapper.find('#reg-tipo-ocupante').setValue('INQUILINO');

    await wrapper.find('#register-form').trigger('submit.prevent');
    await flushPromises();

    expect(regSpy).toHaveBeenCalledOnce();
    expect(pushMock).toHaveBeenCalledWith('/espera-aprobacion');
  });

  it('muestra banner de error cuando falla el registro en el backend', async () => {
    vi.spyOn(apiClient, 'apiRequest').mockRejectedValueOnce(new Error('offline'));
    const store = useAuthStore();
    store.errorMessage = 'La cédula o el correo ya están registrados.';
    vi.spyOn(store, 'register').mockRejectedValueOnce(new Error('Conflict'));

    const wrapper = mount(RegisterView);
    await flushPromises();

    await wrapper.find('#reg-nombre').setValue('Pedro');
    await wrapper.find('#reg-cedula').setValue('V-1');
    await wrapper.find('#reg-correo').setValue('pedro@test.com');
    await wrapper.find('#reg-telefono').setValue('0414');
    await wrapper.find('#reg-password').setValue('Password123!');
    await wrapper.find('#register-form').trigger('submit.prevent');
    await flushPromises();

    expect(wrapper.find('.banner--error').text()).toContain('ya están registrados');
  });
});
