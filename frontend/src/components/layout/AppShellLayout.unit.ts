// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import AppShellLayout from './AppShellLayout.vue';
import { useAuthStore } from '../../stores/authStore';
import { useAccessAmenitiesStore } from '../../stores/accessAmenitiesStore';
import { useFinanceStore } from '../../stores/financeStore';
import { useGovernanceStore } from '../../stores/governanceStore';
import { useOperationsStore } from '../../stores/operationsStore';
import * as apiClient from '../../services/apiClient';

const pushMock = vi.fn();

vi.mock('vue-router', () => ({
  RouterView: { template: '<div id="default-router-view-stub">Router Child</div>' },
  useRoute: () => ({ path: '/dashboard' }),
  useRouter: () => ({ push: pushMock }),
}));

describe('AppShellLayout.vue (Anti-JSDOM Geometry & Navigation)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pushMock.mockReset();
    HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
      this.setAttribute('open', '');
    });
    HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
      this.removeAttribute('open');
    });
  });

  it('renderiza SidebarNav, main in-flow con AppFooter, BottomNavBar, cajón móvil y botón de cierre móvil', async () => {
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
    expect(wrapper.find('#btn-mobile-menu').exists()).toBe(true);
    expect(wrapper.find('#btn-mobile-logout').exists()).toBe(true);

    // Botón de menú móvil abre cajón completo y navega
    expect(wrapper.find('#mobile-nav-drawer').exists()).toBe(false);
    await wrapper.find('#btn-mobile-menu').trigger('click');
    await flushPromises();
    expect(wrapper.find('#mobile-nav-drawer').exists()).toBe(true);
    await wrapper.find('#drawer-side-consultas').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/consultas');
    await flushPromises();
    expect(wrapper.find('#mobile-nav-drawer').exists()).toBe(false);

    // Botón de tema y ayuda contextual universal
    expect(wrapper.find('#btn-theme-toggle').exists()).toBe(true);
    const btnHelp = wrapper.find('#btn-contextual-help');
    expect(btnHelp.exists()).toBe(true);
    expect(wrapper.find('#dialog-contextual-help').exists()).toBe(false);

    await btnHelp.trigger('click');
    expect(wrapper.find('#dialog-contextual-help').exists()).toBe(true);
    expect(wrapper.find('#help-screen-title').text()).toContain('Tu Hogar Hoy');

    await wrapper.find('#btn-close-help').trigger('click');
    expect(wrapper.find('#dialog-contextual-help').exists()).toBe(false);

    // Navegación
    await wrapper.find('#nav-pagar').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/finanzas/reportar-pago');

    // Logout móvil directo
    vi.spyOn(apiClient, 'apiRequest').mockResolvedValue({ message: 'ok' });
    await wrapper.find('#btn-mobile-logout').trigger('click');
    await flushPromises();
    expect(authStore.isAuthenticated).toBe(false);
    expect(pushMock).toHaveBeenCalledWith('/login');

    // Render con fallback <RouterView /> cuando no se pasa slot explícito
    const wrapperRouter = mount(AppShellLayout);
    expect(wrapperRouter.find('#default-router-view-stub').text()).toBe('Router Child');

    // Logout lateral
    authStore.setProfileForTesting({
      id: 3,
      nombre: 'Elena Torres',
      cedula: 'V-11223344',
      correo: 'elena@test.com',
      telefono: '04141112233',
      es_activo: true,
      rol: 'PROPIETARIO',
    });
    await wrapperRouter.find('#btn-sidebar-logout').trigger('click');
    await flushPromises();
    expect(authStore.isAuthenticated).toBe(false);
  });

  it('refleja isStale de stores de dominio en StaleDataBanner y permite descartar rbacNotice (Hito 17.2)', async () => {
    const authStore = useAuthStore();
    const financeStore = useFinanceStore();
    const governanceStore = useGovernanceStore();

    authStore.setRbacNotice('No posee permisos para acceder a la sección solicitada.');
    financeStore.isStale = true;
    financeStore.errorMessage = 'Finanzas en caché local.';

    const wrapper = mount(AppShellLayout, {
      slots: { default: '<div>Ok</div>' },
    });

    expect(wrapper.find('#rbac-notice-banner').text()).toContain('No posee permisos');
    expect(wrapper.find('#stale-data-banner').exists()).toBe(true);
    expect(wrapper.find('#stale-data-banner').text()).toContain('Finanzas en caché local.');

    await wrapper.find('#btn-dismiss-rbac-notice').trigger('click');
    expect(wrapper.find('#rbac-notice-banner').exists()).toBe(false);

    financeStore.isStale = false;
    governanceStore.isStale = true;
    governanceStore.error = 'Consultas offline';
    await wrapper.vm.$nextTick();
    expect(wrapper.find('#stale-data-banner').text()).toContain('Consultas offline');

    const opsStore = useOperationsStore();
    const accStore = useAccessAmenitiesStore();
    governanceStore.isStale = false;
    opsStore.isStale = true;
    opsStore.errorMessage = 'Incidencias offline';
    await wrapper.vm.$nextTick();
    expect(wrapper.find('#stale-data-banner').text()).toContain('Incidencias offline');

    opsStore.isStale = false;
    accStore.isStale = true;
    accStore.error = null;
    await wrapper.vm.$nextTick();
    expect(wrapper.find('#stale-data-banner').exists()).toBe(true);
  });
});
