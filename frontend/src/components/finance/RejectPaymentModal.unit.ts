import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import RejectPaymentModal from './RejectPaymentModal.vue';

describe('RejectPaymentModal.vue', () => {
  beforeEach(() => {
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();
  });

  it('bloquea la confirmación cuando el motivo tiene menos de 5 caracteres y emite confirm al ser válido', async () => {
    const wrapper = mount(RejectPaymentModal, {
      props: { open: true, pagoId: 44 },
    });
    await flushPromises();
    expect(wrapper.find('#modal-reject-reason').attributes('open')).toBeUndefined();
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();

    const confirmBtn = wrapper.find('#btn-confirm-reject');
    expect((confirmBtn.element as HTMLButtonElement).disabled).toBe(true);

    await wrapper.find('#input-reject-motivo').setValue('cort');
    await wrapper.find('#input-reject-motivo').trigger('blur');
    await wrapper.find('form').trigger('submit.prevent');
    expect(wrapper.emitted('confirm')).toBeUndefined();

    await wrapper.find('#input-reject-motivo').setValue('Referencia bancaria inválida en Banesco');
    expect((confirmBtn.element as HTMLButtonElement).disabled).toBe(false);

    await wrapper.find('form').trigger('submit.prevent');
    expect(wrapper.emitted('confirm')?.[0]).toEqual([
      {
        pagoId: 44,
        motivo: 'Referencia bancaria inválida en Banesco',
      },
    ]);

    await wrapper.find('#btn-cancel-reject').trigger('click');
    expect(wrapper.emitted('close')).toBeTruthy();

    await wrapper.setProps({ open: false });
    expect(wrapper.find('#modal-reject-reason').attributes('open')).toBeUndefined();
  });

  it('cierra el diálogo nativo si estaba abierto al pasar open=false y maneja evento close / pagoId=null', async () => {
    const closeSpy = vi.fn(function (this: HTMLDialogElement) {
      Object.defineProperty(this, 'open', { configurable: true, value: false });
    });
    HTMLDialogElement.prototype.close = closeSpy;

    const wrapper = mount(RejectPaymentModal, {
      props: { open: true, pagoId: null },
    });
    await flushPromises();

    // Con pagoId=null aunque el motivo tenga >=5 chars no emite confirm
    await wrapper.find('#input-reject-motivo').setValue('Motivo válido pero sin ID');
    await wrapper.find('form').trigger('submit.prevent');
    expect(wrapper.emitted('confirm')).toBeUndefined();

    // Evento nativo @close mientras open=true debe emitir 'close'
    await wrapper.find('#modal-reject-reason').trigger('close');
    expect(wrapper.emitted('close')).toHaveLength(1);

    // Simular dialog.open = true y cerrar vía prop open=false
    const dialogEl = wrapper.find('#modal-reject-reason').element as HTMLDialogElement;
    Object.defineProperty(dialogEl, 'open', { configurable: true, value: true });
    await wrapper.setProps({ open: false });
    expect(closeSpy).toHaveBeenCalled();

    // Con open=false, un evento close nativo no re-emite close
    await wrapper.find('#modal-reject-reason').trigger('close');
    expect(wrapper.emitted('close')).toHaveLength(1);
  });
});
