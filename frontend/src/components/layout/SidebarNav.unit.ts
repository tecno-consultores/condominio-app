import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { useAuthStore } from '../../stores/authStore';
import SidebarNav from './SidebarNav.vue';

describe('SidebarNav.vue', () => {
  it('muestra nombre de usuario, rol, 3 grupos semánticos, iconos SVG, enlaces RBAC filtrados y emite navigate/logout', async () => {
    const wrapper = mount(SidebarNav, {
      props: {
        userName: 'María Gómez',
        role: 'TESORERO',
        currentPath: '/dashboard',
      },
    });

    expect(wrapper.text()).toContain('María Gómez');
    expect(wrapper.text()).toContain('TESORERO');
    expect(wrapper.text()).toContain('Mi Hogar y Finanzas');
    expect(wrapper.text()).toContain('Comunidad y Gobernanza');
    expect(wrapper.text()).toContain('Operaciones y Junta Directiva');
    expect(wrapper.find('#btn-sidebar-theme-toggle').exists()).toBe(true);
    expect(wrapper.findAll('button.sidebar__link svg').length).toBeGreaterThan(0);

    expect(wrapper.find('#side-dashboard').attributes('aria-current')).toBe('page');
    expect(wrapper.find('#side-revision-pagos').exists()).toBe(true);
    expect(wrapper.find('#side-cierre-mensual').exists()).toBe(true);
    expect(wrapper.find('#side-facturacion').exists()).toBe(true);
    expect(wrapper.find('#side-estructura').exists()).toBe(false);
    expect(wrapper.find('#side-junta').exists()).toBe(false);
    expect(wrapper.find('#side-garita-qr').exists()).toBe(false);

    await wrapper.find('#side-pagar').trigger('click');
    expect(wrapper.emitted('navigate')?.[0]).toEqual(['/finanzas/reportar-pago']);

    await wrapper.find('#btn-sidebar-logout').trigger('click');
    expect(wrapper.emitted('logout')).toBeTruthy();

    setActivePinia(createPinia());
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 1,
      nombre: 'Presidencia',
      cedula: 'V-1',
      correo: 'pres@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'PRESIDENTE',
    });

    const fallbackWrapper = mount(SidebarNav, {
      props: {
        userName: 'Presidencia',
        role: null,
        currentPath: '/admin/junta',
      },
    });
    expect(fallbackWrapper.text()).toContain('PRESIDENTE');
    expect(fallbackWrapper.find('#side-junta').exists()).toBe(true);
    expect(fallbackWrapper.find('#side-garita-qr').exists()).toBe(true);
  });
});
