import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import PendingApprovalView from './PendingApprovalView.vue';
import { useAuthStore } from '../../stores/authStore';

const pushMock = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}));

describe('PendingApprovalView.vue (Pantalla de Contención Fantasma)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pushMock.mockReset();
  });

  it('muestra aviso cuando continúa fantasma, redirige a /dashboard al ser activado y permite cerrar sesión', async () => {
    const store = useAuthStore();
    const wrapper = mount(PendingApprovalView);

    expect(wrapper.find('#ghost-lock-screen').exists()).toBe(true);
    expect(wrapper.text()).toContain('Registro completado. Esperando validación de la Junta');

    // 1. Sigue siendo fantasma -> muestra mensaje de espera
    vi.spyOn(store, 'fetchProfile').mockResolvedValueOnce({
      id: 9,
      nombre: 'Fantasma',
      cedula: 'V-9',
      correo: 'f@test.com',
      telefono: '0414',
      es_activo: false,
      rol: 'FANTASMA',
    });
    await wrapper.find('#btn-refresh-status').trigger('click');
    await flushPromises();
    expect(wrapper.find('#ghost-status-msg').text()).toContain('continúa en espera');

    // 2. Ya fue activado por el Presidente -> redirige a /dashboard
    vi.spyOn(store, 'fetchProfile').mockResolvedValueOnce({
      id: 9,
      nombre: 'Residente Aprobado',
      cedula: 'V-9',
      correo: 'f@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });
    await wrapper.find('#btn-refresh-status').trigger('click');
    await flushPromises();
    expect(pushMock).toHaveBeenCalledWith('/dashboard');

    // 3. Cerrar sesión -> limpia store y redirige a /login
    await wrapper.find('#btn-logout').trigger('click');
    expect(store.isAuthenticated).toBe(false);
    expect(pushMock).toHaveBeenCalledWith('/login');
  });
});
