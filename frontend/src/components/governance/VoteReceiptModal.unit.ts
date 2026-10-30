import { describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import VoteReceiptModal from './VoteReceiptModal.vue';

describe('VoteReceiptModal.vue', () => {
  const reciboCompleto = {
    voto_id: 15,
    consulta_id: 4,
    titulo_consulta: 'Carta Consulta #04-2026',
    unidad_id: 3,
    identificador_unidad: 'A-03',
    usuario_id: 2,
    opcion_id: 10,
    opcion_etiqueta: 'APROBAR PRESUPUESTO A',
    alicuota_capturada: '33.3333',
    participacion_total_alicuota: '66.6700',
    quorum_minimo_alicuota: '66.6700',
    fecha_voto: '2026-10-30T12:00:00Z',
    ip_hash: 'a'.repeat(64),
    firma_hmac: 'b'.repeat(64),
    mensaje_verificacion: 'VOTO|v1|4|3|10|33.3333|2026-10-30T12:00:00Z',
  };

  it('renderiza el recibo criptográfico HMAC-SHA256 y emite close al cerrar o clic fuera', async () => {
    const wrapper = mount(VoteReceiptModal, {
      props: {
        open: true,
        recibo: reciboCompleto,
      },
    });

    expect(wrapper.find('#modal-vote-receipt').exists()).toBe(true);
    expect(wrapper.find('#receipt-unidad').text()).toBe('A-03');
    expect(wrapper.find('#receipt-opcion').text()).toBe('APROBAR PRESUPUESTO A');
    expect(wrapper.find('#receipt-alicuota-capturada').text()).toBe('33.3333%');
    expect(wrapper.find('#receipt-firma-hmac').text()).toBe('b'.repeat(64));
    expect(wrapper.find('#receipt-mensaje-verificacion').text()).toContain('VOTO|v1|4|3|10');

    await wrapper.find('#btn-close-vote-receipt').trigger('click');
    expect(wrapper.emitted('close')).toBeTruthy();

    // Probar fallback light-dismiss en clic sobre dialog fuera de coordenadas
    const dialogEl = wrapper.find('#modal-vote-receipt').element as HTMLDialogElement;
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

    await wrapper.find('#modal-vote-receipt').trigger('click', { clientX: 150, clientY: 150 });
    expect(wrapper.emitted('close')?.length).toBe(1);

    await wrapper.find('#modal-vote-receipt').trigger('click', { clientX: 10, clientY: 10 });
    expect(wrapper.emitted('close')?.length).toBe(2);
  });

  it('soporta recibo resumido sin mensaje_verificacion y no renderiza si open es false', () => {
    const closedWrapper = mount(VoteReceiptModal, {
      props: { open: false, recibo: reciboCompleto },
    });
    expect(closedWrapper.find('#modal-vote-receipt').exists()).toBe(false);

    const resumenWrapper = mount(VoteReceiptModal, {
      props: {
        open: true,
        recibo: {
          voto_id: 9,
          unidad_id: 1,
          identificador_unidad: 'A-01',
          opcion_id: 2,
          opcion_etiqueta: 'SÍ',
          alicuota_capturada: '25.0000',
          fecha_voto: '2026-10-30T10:00:00Z',
          firma_hmac: 'c'.repeat(64),
        },
        tituloConsulta: 'Asamblea Extraordinaria',
      },
    });
    expect(resumenWrapper.text()).toContain('Asamblea Extraordinaria');
    expect(resumenWrapper.find('#receipt-mensaje-verificacion').exists()).toBe(false);
  });
});
