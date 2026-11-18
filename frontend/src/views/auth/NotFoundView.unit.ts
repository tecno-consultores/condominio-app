import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '../../stores/authStore';
import NotFoundView from './NotFoundView.vue';

const pushMock = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}));

describe('NotFoundView.vue (Ruta Catch-All 404)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pushMock.mockReset();
  });

  it('redirige al destino correcto según el estado de sesión del usuario', async () => {
    const authStore = useAuthStore();
    const wrapper = mount(NotFoundView);
    expect(wrapper.text()).toContain('Página no encontrada');

    await wrapper.find('#btn-go-home').trigger('click');
    expect(pushMock).toHaveBeenLastCalledWith('/login');

    authStore.setProfileForTesting({
      id: 9,
      nombre: 'Fantasma',
      cedula: 'V-9',
      correo: 'f@test.com',
      telefono: '0414',
      es_activo: false,
      rol: 'FANTASMA',
    });
    await wrapper.find('#btn-go-home').trigger('click');
    expect(pushMock).toHaveBeenLastCalledWith('/espera-aprobacion');

    authStore.setProfileForTesting({
      id: 1,
      nombre: 'Ana',
      cedula: 'V-1',
      correo: 'a@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });
    await wrapper.find('#btn-go-home').trigger('click');
    expect(pushMock).toHaveBeenLastCalledWith('/dashboard');
  });
});
