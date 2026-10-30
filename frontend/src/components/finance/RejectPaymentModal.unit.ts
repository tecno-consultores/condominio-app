import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import RejectPaymentModal from './RejectPaymentModal.vue';

describe('RejectPaymentModal.vue', () => {
  it('bloquea la confirmación cuando el motivo tiene menos de 5 caracteres y emite confirm al ser válido', async () => {
    const wrapper = mount(RejectPaymentModal, {
      props: { open: true, pagoId: 44 },
    });

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
});
