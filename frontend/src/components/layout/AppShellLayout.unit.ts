import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import AppShellLayout from './AppShellLayout.vue';
import { useAuthStore } from '../../stores/authStore';

const pushMock = vi.fn();

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/dashboard' }),
  useRouter: () => ({ push: pushMock }),
}));

describe('AppShellLayout.vue (Anti-JSDOM Geometry & Navigation)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pushMock.mockReset();
  });

  it('renderiza SidebarNav, main in-flow con AppFooter y BottomNavBar, y gestiona navegación/logout', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 3,
      nombre: 'Elena Torres',
      cedula: 'V-11223344',
      correo: 'elena@test.com',
      telefono: '04141112233',
      es_activo: true,
      rol: 'PROPIETARIO',
    });

    const wrapper = mount(AppShellLayout, {
      slots: {
        default: '<div id="slot-content">Contenido Principal</div>',
      },
    });

    expect(wrapper.find('#app-main-content').exists()).toBe(true);
    expect(wrapper.find('#slot-content').text()).toBe('Contenido Principal');
    expect(wrapper.find('#app-inflow-footer').exists()).toBe(true);
    expect(wrapper.find('#mobile-bottom-nav').exists()).toBe(true);
    expect(wrapper.find('#desktop-sidebar').exists()).toBe(true);

    await wrapper.find('#nav-pagar').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/finanzas/reportar-pago');

    await wrapper.find('#btn-sidebar-logout').trigger('click');
    expect(authStore.isAuthenticated).toBe(false);
    expect(pushMock).toHaveBeenCalledWith('/login');
  });
});
