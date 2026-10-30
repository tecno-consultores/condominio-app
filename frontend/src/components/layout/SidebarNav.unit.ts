import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import SidebarNav from './SidebarNav.vue';

describe('SidebarNav.vue', () => {
  it('muestra nombre de usuario, rol activo y emite eventos navigate y logout', async () => {
    const wrapper = mount(SidebarNav, {
      props: {
        userName: 'María Gómez',
        role: 'TESORERO',
        currentPath: '/dashboard',
      },
    });

    expect(wrapper.text()).toContain('María Gómez');
    expect(wrapper.text()).toContain('TESORERO');
    expect(wrapper.find('#side-dashboard').attributes('aria-current')).toBe('page');

    await wrapper.find('#side-pagar').trigger('click');
    expect(wrapper.emitted('navigate')?.[0]).toEqual(['/finanzas/reportar-pago']);

    await wrapper.find('#btn-sidebar-logout').trigger('click');
    expect(wrapper.emitted('logout')).toBeTruthy();

    const fallbackWrapper = mount(SidebarNav, {
      props: {
        userName: 'Invitado',
        role: null,
        currentPath: '/incidencias',
      },
    });
    expect(fallbackWrapper.text()).toContain('RESIDENTE');
  });
});
