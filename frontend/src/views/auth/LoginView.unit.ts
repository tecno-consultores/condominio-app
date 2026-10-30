import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import LoginView from './LoginView.vue';
import { useAuthStore } from '../../stores/authStore';

const pushMock = vi.fn();
let currentQuery: Record<string, string> = {};

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
  useRoute: () => ({ query: currentQuery }),
}));

describe('LoginView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pushMock.mockReset();
    currentQuery = {};
  });

  it('valida campos vacíos, alterna visibilidad de contraseña y sincroniza aria-invalid en blur/input', async () => {
    const wrapper = mount(LoginView, {
      global: {
        stubs: { 'router-link': { template: '<a><slot /></a>' } },
      },
    });

    await wrapper.find('#login-form').trigger('submit.prevent');
    expect(wrapper.find('.banner--error').text()).toContain('Por favor ingrese su correo');

    const passInput = wrapper.find('#login-password');
    expect(passInput.attributes('type')).toBe('password');
    await wrapper.find('#btn-toggle-password').trigger('click');
    expect(wrapper.find('#login-password').attributes('type')).toBe('text');

    const emailInput = wrapper.find('#login-correo');
    await emailInput.setValue('correo-invalido');
    await emailInput.trigger('blur');
    expect(emailInput.attributes('aria-invalid')).toBeDefined();
    await emailInput.setValue('vecino@condominio.test');
    await emailInput.trigger('input');
  });

  it('redirige a /dashboard para usuarios activos, a /espera-aprobacion para fantasmas y muestra error en 401', async () => {
    currentQuery = { redirect: '/incidencias' };
    const store = useAuthStore();
    const wrapper = mount(LoginView, {
      global: {
        stubs: { 'router-link': { template: '<a><slot /></a>' } },
      },
    });

    // 1. Login exitoso de usuario activo con redirect seguro
    vi.spyOn(store, 'login').mockResolvedValueOnce({
      id: 1,
      nombre: 'Residente Activo',
      cedula: 'V-1',
      correo: 'activo@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });

    await wrapper.find('#login-correo').setValue('activo@test.com');
    await wrapper.find('#login-password').setValue('Password123!');
    await wrapper.find('#login-form').trigger('submit.prevent');
    await flushPromises();
    expect(pushMock).toHaveBeenCalledWith('/incidencias');

    // 1b. Sin redirect seguro -> va a /dashboard
    currentQuery.redirect = 'https://evil.com';
    vi.spyOn(store, 'login').mockResolvedValueOnce({
      id: 1,
      nombre: 'Residente Activo',
      cedula: 'V-1',
      correo: 'activo@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PROPIETARIO',
    });
    await wrapper.find('#login-form').trigger('submit.prevent');
    await flushPromises();
    expect(pushMock).toHaveBeenCalledWith('/dashboard');

    // 2. Login de Usuario Fantasma -> redirige a /espera-aprobacion
    vi.spyOn(store, 'login').mockResolvedValueOnce({
      id: 9,
      nombre: 'Fantasma',
      cedula: 'V-9',
      correo: 'fantasma@test.com',
      telefono: '0414',
      es_activo: false,
      rol: 'FANTASMA',
    });
    await wrapper.find('#login-form').trigger('submit.prevent');
    await flushPromises();
    expect(pushMock).toHaveBeenCalledWith('/espera-aprobacion');

    // 3. Fallo de credenciales -> muestra .banner--error
    store.errorMessage = 'Credenciales inválidas';
    vi.spyOn(store, 'login').mockRejectedValueOnce(new Error('Credenciales inválidas'));
    await wrapper.find('#login-form').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('.banner--error').text()).toContain('Credenciales inválidas');
  });
});
