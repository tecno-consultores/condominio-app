import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MobileNavDrawer from './MobileNavDrawer.vue';

describe('MobileNavDrawer.vue — Cajón móvil completo y cierre de sesión < 768px', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    HTMLDialogElement.prototype.showModal = vi.fn(function (this: HTMLDialogElement) {
      this.setAttribute('open', '');
    });
    HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
      this.removeAttribute('open');
    });
  });

  it('muestra todas las rutas autorizadas por rol, navega y dispara logout/close', async () => {
    const wrapper = mount(MobileNavDrawer, {
      props: {
        open: false,
        userName: 'Elena Torres',
        role: 'PROPIETARIO',
        currentPath: '/consultas',
      },
    });
    expect(wrapper.find('#mobile-nav-drawer').exists()).toBe(false);

    await wrapper.setProps({ open: true });
    await flushPromises();
    expect(wrapper.find('#mobile-nav-drawer').exists()).toBe(true);
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();

    expect(wrapper.find('#drawer-side-consultas').attributes('aria-current')).toBe('page');
    expect(wrapper.find('#drawer-side-reservas').exists()).toBe(true);
    expect(wrapper.find('#drawer-side-junta').exists()).toBe(false);

    await wrapper.find('#drawer-side-reservas').trigger('click');
    expect(wrapper.emitted('navigate')?.[0]).toEqual(['/reservas/areas']);
    expect(wrapper.emitted('close')).toBeTruthy();

    await wrapper.find('#btn-mobile-drawer-logout').trigger('click');
    expect(wrapper.emitted('logout')).toBeTruthy();

    await wrapper.find('#btn-close-mobile-drawer').trigger('click');
    expect(wrapper.emitted('close')?.length).toBeGreaterThanOrEqual(2);

    // Cancel nativo, backdrop click y respaldo role=null -> RESIDENTE
    const drawer = wrapper.find('#mobile-nav-drawer');
    await drawer.trigger('cancel');
    await drawer.trigger('pointerdown');
    await drawer.trigger('pointerup');
    await drawer.trigger('click');
    expect(wrapper.emitted('close')?.length).toBeGreaterThanOrEqual(4);

    await wrapper.setProps({ role: null });
    expect(wrapper.text()).toContain('RESIDENTE · Elena Torres');

    const drawerEl = drawer.element as HTMLDialogElement;
    Object.defineProperty(drawerEl, 'open', { configurable: true, value: true });
    await wrapper.setProps({ open: false });
    expect(HTMLDialogElement.prototype.close).toHaveBeenCalled();
  });
});
