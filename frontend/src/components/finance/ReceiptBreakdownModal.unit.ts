import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ReceiptBreakdownModal from './ReceiptBreakdownModal.vue';
import type { ReciboDesgloseDTO } from '../../stores/financeStore';

const sampleDesglose: ReciboDesgloseDTO = {
  recibo_id: 7,
  unidad_id: 1,
  identificador_unidad: 'Apto 1-A',
  alicuota_aplicada: '33.3333',
  periodo: '2026-10',
  monto_usd: '35.00',
  monto_pagado_usd: '0.00',
  saldo_pendiente_usd: '35.00',
  credito_descontado_usd: '10.00',
  estado: 'PENDIENTE',
  bloqueado: false,
  items: [
    {
      id: 1,
      recibo_id: 7,
      tipo_item: 'GASTO_COMUN',
      descripcion: 'Cuota parte de gastos comunes (2026-10)',
      monto_usd: '45.00',
    },
    {
      id: 2,
      recibo_id: 7,
      tipo_item: 'ABONO_CREDITO_PREVIO',
      descripcion: 'Abono automático de saldo a favor disponible',
      monto_usd: '-10.00',
    },
  ],
};

describe('ReceiptBreakdownModal.vue', () => {
  beforeEach(() => {
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();
  });

  it('renderiza las líneas del recibo, alícuota y emite close al pulsar #btn-close-desglose', async () => {
    const wrapper = mount(ReceiptBreakdownModal, {
      props: {
        open: true,
        desglose: sampleDesglose,
      },
    });
    await flushPromises();

    const dialog = wrapper.find('#modal-recibo-desglose');
    expect(dialog.exists()).toBe(true);
    expect(dialog.attributes('open')).toBeUndefined();
    expect(dialog.attributes('closedby')).toBe('any');
    expect(wrapper.find('#btn-close-desglose').attributes('autofocus')).toBeDefined();
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();
    expect(wrapper.text()).toContain('Apto 1-A');
    expect(wrapper.text()).toContain('33.3333%');
    expect(wrapper.findAll('.breakdown-modal__item')).toHaveLength(2);
    expect(wrapper.find('#breakdown-saldo-pendiente').text()).toContain('$35.00 USD');

    const dialogEl = dialog.element as HTMLDialogElement;
    vi.spyOn(dialogEl, 'getBoundingClientRect').mockReturnValue({
      top: 100,
      left: 100,
      width: 200,
      height: 200,
      bottom: 300,
      right: 300,
      x: 100,
      y: 100,
      toJSON: () => ({}),
    });
    await dialog.trigger('click', { clientX: 150, clientY: 150 });
    expect(wrapper.emitted('close')).toBeUndefined();

    // Arrastre que empieza dentro y suelta fuera NO debe cerrar
    await dialog.trigger('pointerdown', { clientX: 150, clientY: 150 });
    await dialog.trigger('pointerup', { clientX: 5, clientY: 5 });
    await dialog.trigger('click', { clientX: 5, clientY: 5 });
    expect(wrapper.emitted('close')).toBeUndefined();

    // Presión y liberación fuera SÍ debe cerrar
    await dialog.trigger('pointerdown', { clientX: 5, clientY: 5 });
    await dialog.trigger('pointerup', { clientX: 5, clientY: 5 });
    expect(wrapper.emitted('close')).toHaveLength(1);

    await dialog.trigger('click', { clientX: 10, clientY: 10 });
    expect(wrapper.emitted('close')).toHaveLength(2);

    await wrapper.find('#btn-close-desglose').trigger('click');
    expect(wrapper.emitted('close')).toHaveLength(3);

    // Rama nativa closedBy y evento en elemento hijo
    Object.defineProperty(HTMLDialogElement.prototype, 'closedBy', {
      configurable: true,
      value: 'any',
    });
    try {
      await dialog.trigger('pointerdown', { clientX: 0, clientY: 0 });
      await dialog.trigger('pointerup', { clientX: 0, clientY: 0 });
      await dialog.trigger('click', { clientX: 0, clientY: 0 });
      expect(wrapper.emitted('close')).toHaveLength(3);
    } finally {
      delete (HTMLDialogElement.prototype as unknown as Record<string, unknown>).closedBy;
    }
    await wrapper.find('.breakdown-modal__card').trigger('click', { clientX: 0, clientY: 0 });
    expect(wrapper.emitted('close')).toHaveLength(3);

    await wrapper.setProps({ open: false });
    expect(wrapper.find('#modal-recibo-desglose').exists()).toBe(false);
  });
});
