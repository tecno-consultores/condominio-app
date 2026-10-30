import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
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
  it('renderiza las líneas del recibo, alícuota y emite close al pulsar #btn-close-desglose', async () => {
    const wrapper = mount(ReceiptBreakdownModal, {
      props: {
        open: true,
        desglose: sampleDesglose,
      },
    });

    expect(wrapper.find('#modal-recibo-desglose').exists()).toBe(true);
    expect(wrapper.text()).toContain('Apto 1-A');
    expect(wrapper.text()).toContain('33.3333%');
    expect(wrapper.findAll('.breakdown-modal__item')).toHaveLength(2);
    expect(wrapper.find('#breakdown-saldo-pendiente').text()).toContain('$35.00 USD');

    await wrapper.find('#btn-close-desglose').trigger('click');
    expect(wrapper.emitted('close')).toHaveLength(1);

    await wrapper.setProps({ open: false });
    expect(wrapper.find('#modal-recibo-desglose').exists()).toBe(false);
  });
});
