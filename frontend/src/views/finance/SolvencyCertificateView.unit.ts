import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SolvencyCertificateView from './SolvencyCertificateView.vue';
import { useFinanceStore } from '../../stores/financeStore';
import { useOperationsStore } from '../../stores/operationsStore';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/finanzas/solvencia' }),
}));

describe('SolvencyCertificateView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('emite certificado de solvencia (#qr-solvencia-badge) y verifica su firma HMAC-SHA256', async () => {
    const financeStore = useFinanceStore();
    const operationsStore = useOperationsStore();
    operationsStore.data.unidades = [
      { id: 1, identificador: 'Apto 1-A', estructura_id: 1, alicuota: '25.0000' },
    ];
    vi.spyOn(operationsStore, 'fetchAdminData').mockResolvedValue();

    const emitirSpy = vi
      .spyOn(financeStore, 'emitirCertificadoSolvencia')
      .mockImplementation(async () => {
        financeStore.data.certificadoSolvenciaActivo = {
          id: 1,
          folio: 'SOLV-202610-0001-ABCD',
          unidad_id: 1,
          identificador_unidad: 'Apto 1-A',
          emitido_por_id: 1,
          fecha_emision: '2026-10-30T10:00:00Z',
          fecha_vencimiento: '2026-10-31',
          deuda_verificada_usd: '0.00',
          firma_hmac: '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
          qr_token: 'U09MVnx2MQ.1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        };
        return financeStore.data.certificadoSolvenciaActivo;
      });

    const verificarSpy = vi
      .spyOn(financeStore, 'verificarCertificadoSolvencia')
      .mockImplementation(async () => {
        financeStore.data.verificacionSolvencia = {
          valido: true,
          folio: 'SOLV-202610-0001-ABCD',
          unidad_id: 1,
          identificador_unidad: 'Apto 1-A',
          fecha_vencimiento: '2026-10-31',
          vigente: true,
          deuda_verificada_usd: '0.00',
          firma_hmac: '1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        };
        return financeStore.data.verificacionSolvencia;
      });

    const wrapper = mount(SolvencyCertificateView);
    await flushPromises();

    // Emitir certificado seleccionando unidad
    await wrapper.find('#input-solvencia-unidad-id').setValue('1');
    await wrapper.find('#btn-emitir-solvencia').trigger('click');
    await flushPromises();
    expect(emitirSpy).toHaveBeenCalledOnce();
    expect(wrapper.find('#qr-solvencia-badge').exists()).toBe(true);
    expect(wrapper.find('#qr-solvencia-badge').text()).toContain('SOLV-202610-0001-ABCD');

    // Validación con firma vacía
    await wrapper.find('#input-verificar-folio').setValue('SOLV-202610-0001-ABCD');
    await wrapper.find('#input-verificar-sig').setValue('corta');
    await wrapper.find('#form-verificar-solvencia').trigger('submit.prevent');
    expect(wrapper.find('#solvencia-validation-error').text()).toContain('HMAC-SHA256');

    // Verificación válida
    await wrapper
      .find('#input-verificar-sig')
      .setValue('1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef');
    await wrapper.find('#form-verificar-solvencia').trigger('submit.prevent');
    await flushPromises();
    expect(verificarSpy).toHaveBeenCalledOnce();
    expect(wrapper.find('#solvencia-verificacion-result').text()).toContain(
      'CERTIFICADO AUTÉNTICO',
    );

    // Estado inválido, banner de error y fallos de red en emisión/verificación
    financeStore.errorMessage = 'Fallo de red simulado';
    financeStore.data.verificacionSolvencia = {
      valido: false,
      folio: 'SOLV-202610-0001-ABCD',
      unidad_id: 1,
      identificador_unidad: 'Apto 1-A',
      fecha_vencimiento: '2026-10-31',
      vigente: false,
      deuda_verificada_usd: '0.00',
      firma_hmac: '0000',
    };
    emitirSpy.mockRejectedValueOnce(new Error('Insolvente'));
    verificarSpy.mockRejectedValueOnce(new Error('No encontrado'));
    await wrapper.find('#btn-emitir-solvencia').trigger('click');
    await wrapper.find('#form-verificar-solvencia').trigger('submit.prevent');
    await flushPromises();
    expect(wrapper.find('#solvencia-error-banner').exists()).toBe(true);
    expect(wrapper.find('#solvencia-verificacion-result').text()).toContain('INVÁLIDO');
  });
});
