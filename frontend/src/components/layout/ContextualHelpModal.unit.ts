// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import ContextualHelpModal from './ContextualHelpModal.vue';
import { useAuthStore } from '../../stores/authStore';

const mockRoute = {
  path: '/dashboard',
};

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
}));

describe('ContextualHelpModal.vue (Universal Screen Help Dialog)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockRoute.path = '/dashboard';
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();
  });

  it('no renderiza el diálogo si open es false', () => {
    const wrapper = mount(ContextualHelpModal, {
      props: { open: false },
    });
    expect(wrapper.find('#dialog-contextual-help').exists()).toBe(false);
  });

  it('renderiza el diálogo con selectores contractuales cuando open es true', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 1,
      nombre: 'Carlos Residente',
      cedula: 'V-12345678',
      correo: 'carlos@test.com',
      telefono: '04121234567',
      es_activo: true,
      rol: 'PROPIETARIO',
    });

    const wrapper = mount(ContextualHelpModal, {
      props: {
        open: true,
        path: '/finanzas/reportar-pago',
      },
    });

    expect(wrapper.find('#dialog-contextual-help').exists()).toBe(true);
    expect(wrapper.find('#dialog-contextual-help').attributes('open')).toBeUndefined();
    expect(wrapper.find('#dialog-contextual-help').attributes('closedby')).toBe('any');
    expect(wrapper.find('.help-dialog__action-btn').attributes('autofocus')).toBeDefined();
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();
    expect(wrapper.find('#help-screen-title').text()).toBe('Asistente de Reporte de Pagos');
    expect(wrapper.find('#help-screen-purpose').exists()).toBe(true);
    expect(wrapper.find('#help-steps-list').exists()).toBe(true);
    expect(wrapper.findAll('.help-steps-item').length).toBe(3);
    expect(wrapper.find('#help-tips-list').exists()).toBe(true);
    expect(wrapper.findAll('.help-tips-item').length).toBeGreaterThan(0);
    expect(wrapper.find('#btn-close-help').exists()).toBe(true);
  });

  it('emite evento close al presionar el botón de cierre o la acción principal', async () => {
    const wrapper = mount(ContextualHelpModal, {
      props: {
        open: true,
        path: '/dashboard',
      },
    });

    await wrapper.find('#btn-close-help').trigger('click');
    expect(wrapper.emitted('close')).toBeTruthy();

    await wrapper.find('.help-dialog__action-btn').trigger('click');
    expect(wrapper.emitted('close')?.length).toBe(2);
  });

  it('maneja el click en el backdrop para cerrar el diálogo si se pulsa fuera de la tarjeta', async () => {
    const wrapper = mount(ContextualHelpModal, {
      props: {
        open: true,
        path: '/dashboard',
      },
    });

    const dialog = wrapper.find('#dialog-contextual-help');

    // Simular que el bounding rect está en (10, 10) a (100, 100)
    dialog.element.getBoundingClientRect = vi.fn(() => ({
      top: 10,
      left: 10,
      width: 100,
      height: 100,
      right: 110,
      bottom: 110,
      x: 10,
      y: 10,
      toJSON: () => {},
    }));

    // Click dentro del modal (no emite close)
    await dialog.trigger('click', { clientX: 50, clientY: 50 });
    expect(wrapper.emitted('close')).toBeFalsy();

    // Arrastre que inicia dentro y termina fuera NO debe cerrar
    await dialog.trigger('pointerdown', { clientX: 50, clientY: 50 });
    await dialog.trigger('pointerup', { clientX: 200, clientY: 200 });
    await dialog.trigger('click', { clientX: 200, clientY: 200 });
    expect(wrapper.emitted('close')).toBeFalsy();

    // Presión y liberación fuera SÍ debe cerrar
    await dialog.trigger('pointerdown', { clientX: 200, clientY: 200 });
    await dialog.trigger('pointerup', { clientX: 200, clientY: 200 });
    expect(wrapper.emitted('close')).toHaveLength(1);

    // Click fuera del modal (emite close)
    await dialog.trigger('click', { clientX: 200, clientY: 200 });
    expect(wrapper.emitted('close')).toHaveLength(2);

    // Rama nativa closedBy
    Object.defineProperty(HTMLDialogElement.prototype, 'closedBy', {
      configurable: true,
      value: 'any',
    });
    try {
      await dialog.trigger('pointerdown', { clientX: 200, clientY: 200 });
      await dialog.trigger('pointerup', { clientX: 200, clientY: 200 });
      await dialog.trigger('click', { clientX: 200, clientY: 200 });
      expect(wrapper.emitted('close')).toHaveLength(2);
    } finally {
      delete (HTMLDialogElement.prototype as unknown as Record<string, unknown>).closedBy;
    }
  });

  it('cambia el contenido de la ayuda al actualizar la prop path y role', async () => {
    const wrapper = mount(ContextualHelpModal, {
      props: {
        open: true,
        path: '/incidencias',
        role: 'PROPIETARIO',
      },
    });

    expect(wrapper.find('#help-screen-title').text()).toBe('Embudo de Incidencias Vecinales');

    await wrapper.setProps({
      path: '/operaciones/garita-qr',
      role: 'CONSERJE',
    });

    expect(wrapper.find('#help-screen-title').text()).toBe(
      'Control de Acceso en Garita (Lector QR)',
    );
  });

  it('abre vía watch al cambiar open de false a true y cierra dialog nativo si open pasa a false', async () => {
    const wrapper = mount(ContextualHelpModal, {
      props: { open: false, path: '/dashboard' },
    });
    expect(HTMLDialogElement.prototype.showModal).not.toHaveBeenCalled();

    await wrapper.setProps({ open: true });
    await flushPromises();
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();

    const dialogEl = wrapper.find('#dialog-contextual-help').element as HTMLDialogElement;
    await wrapper.find('#dialog-contextual-help').trigger('close');
    expect(wrapper.emitted('close')).toHaveLength(1);

    Object.defineProperty(dialogEl, 'open', { configurable: true, value: true });
    await wrapper.setProps({ open: false });
    expect(HTMLDialogElement.prototype.close).toHaveBeenCalled();
  });
});
