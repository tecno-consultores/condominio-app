import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import PendingApprovalView from './PendingApprovalView.vue';
import { useAuthStore } from '../../stores/authStore';

const pushMock = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
  useRoute: () => ({ path: '/espera-aprobacion' }),
}));

describe('PendingApprovalView.vue (Pantalla de Contención Fantasma)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pushMock.mockReset();
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();
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

  it('abre y cierra el diálogo de ayuda contextual en espera de aprobación', async () => {
    const wrapper = mount(PendingApprovalView);

    const btnHelp = wrapper.find('#btn-contextual-help');
    expect(btnHelp.exists()).toBe(true);
    expect(wrapper.find('#dialog-contextual-help').exists()).toBe(false);

    await btnHelp.trigger('click');
    expect(wrapper.find('#dialog-contextual-help').exists()).toBe(true);
    expect(wrapper.find('#help-screen-title').text()).toBe('Cuenta Pendiente de Aprobación');

    await wrapper.find('#btn-close-help').trigger('click');
    expect(wrapper.find('#dialog-contextual-help').exists()).toBe(false);
  });
});
