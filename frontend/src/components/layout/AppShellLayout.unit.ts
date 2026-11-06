// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

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
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();
  });

  it('renderiza SidebarNav, main in-flow con AppFooter, BottomNavBar y botón de ayuda contextual', async () => {
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
    expect(wrapper.find('.app-main__body').exists()).toBe(true);
    expect(wrapper.find('#slot-content').text()).toBe('Contenido Principal');
    expect(wrapper.find('#app-inflow-footer').exists()).toBe(true);
    expect(wrapper.find('#mobile-bottom-nav').exists()).toBe(true);
    expect(wrapper.find('#desktop-sidebar').exists()).toBe(true);

    // Botón de ayuda contextual universal
    const btnHelp = wrapper.find('#btn-contextual-help');
    expect(btnHelp.exists()).toBe(true);
    expect(wrapper.find('#dialog-contextual-help').exists()).toBe(false);

    // Al hacer click, se abre el modal
    await btnHelp.trigger('click');
    expect(wrapper.find('#dialog-contextual-help').exists()).toBe(true);
    expect(wrapper.find('#help-screen-title').text()).toContain('Tu Hogar Hoy');

    // Al hacer click en cerrar, se cierra
    await wrapper.find('#btn-close-help').trigger('click');
    expect(wrapper.find('#dialog-contextual-help').exists()).toBe(false);

    // Navegación
    await wrapper.find('#nav-pagar').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/finanzas/reportar-pago');

    // Logout
    await wrapper.find('#btn-sidebar-logout').trigger('click');
    expect(authStore.isAuthenticated).toBe(false);
    expect(pushMock).toHaveBeenCalledWith('/login');
  });
});
