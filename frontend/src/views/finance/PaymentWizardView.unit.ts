import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient } from '../../services/apiClient';
import { useAuthStore } from '../../stores/authStore';
import PaymentWizardView from './PaymentWizardView.vue';

const pushMock = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
  useRoute: () => ({ path: '/finanzas/reportar-pago' }),
}));

function mockPendingDashboardApis(): void {
  vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
    if (url === '/api/finanzas/tasa') {
      return { id: 1, fecha: '2026-10-29', tasa_usd_ves: '36.50' };
    }
    if (url === '/api/finanzas/resumen') {
      return {
        deuda_total_usd: '50.00',
        total_egresos_usd: '200.00',
        gastos_por_categoria: {},
        estado_cobranza: [
          {
            recibo_id: 1,
            unidad_id: 1,
            periodo: '2026-10',
            estado: 'PENDIENTE',
            saldo_usd: '50.00',
          },
        ],
      };
    }
    if (url === '/api/estructura/unidades') {
      return [{ id: 1, identificador: 'Apto A-1', piso: 1, alicuota: '1.0000' }];
    }
    return [];
  });
}

describe('PaymentWizardView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pushMock.mockReset();
    vi.restoreAllMocks();
    mockPendingDashboardApis();
  });

  it('recorre los 3 pasos validando monto, referencia, recibos reales y enviando pago con Idempotency-Key', async () => {
    const authStore = useAuthStore();
    authStore.data = {
      id: 2,
      nombre: 'Ana',
      cedula: 'V-12345678',
      correo: 'ana@condominio.local',
      telefono: '04141234567',
      rol: 'PROPIETARIO',
      es_activo: true,
      unidad_activa_id: 1,
    };

    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
      id: 90,
      recibo_id: 1,
      usuario_id: 2,
      monto: '1825.00',
      moneda: 'VES',
      monto_usd: '50.00',
      tasa_cambio: '36.50',
      metodo_pago: 'PAGO_MOVIL',
      numero_referencia: '88776655',
      url_comprobante: null,
      estado: 'EN_REVISION',
    });

    const wrapper = mount(PaymentWizardView);
    await flushPromises();

    expect(wrapper.find('#select-recibo').text()).toContain('Apto A-1');
    expect(wrapper.find('#select-recibo').text()).not.toContain('Recibo #1');
    expect(wrapper.find('#badge-tipo-cobertura').text()).toContain('PAGO TOTAL');

    // Validar bloqueo con monto 0
    await wrapper.find('#step-1-monto').setValue('0');
    await wrapper.find('#btn-step-1-next').trigger('click');
    expect(wrapper.find('.banner--error').text()).toContain('mayor a cero');

    // Monto válido -> Paso 2
    await wrapper.find('#step-1-monto').setValue('1825.00');
    await wrapper.find('#btn-step-1-next').trigger('click');
    expect(wrapper.find('#step-2-metodo').exists()).toBe(true);

    // Referencia vacía -> Bloqueo en Paso 2
    await wrapper.find('#btn-step-2-next').trigger('click');
    expect(wrapper.find('.banner--error').text()).toContain('referencia bancaria es obligatorio');

    // Referencia válida -> Paso 3
    await wrapper.find('#input-referencia').setValue('88776655');
    await wrapper.find('#btn-step-2-next').trigger('click');
    expect(wrapper.find('#idempotency-key-preview').text()).toBe(
      'Protección anti-duplicado activa',
    );
    expect(wrapper.text()).not.toContain('#1');

    // Confirmar envío
    await wrapper.find('#btn-submit-pago').trigger('click');
    await flushPromises();
    expect(postSpy).toHaveBeenCalledWith(
      '/api/pagos/reportar',
      expect.objectContaining({
        recibo_id: 1,
        monto: '1825.00',
      }),
      expect.objectContaining({ idempotencyKey: expect.any(String) }),
    );
    expect(pushMock).toHaveBeenCalledWith('/dashboard');
  });

  it('rechaza comprobantes > 2 MB y sube archivo válido con FormData antes de reportar pago', async () => {
    const wrapper = mount(PaymentWizardView);
    await flushPromises();
    await wrapper.find('#btn-step-1-next').trigger('click');

    const fileInput = wrapper.find('#step-3-comprobante');
    const oversizedFile = new File([new Uint8Array(2 * 1024 * 1024 + 10)], 'grande.png', {
      type: 'image/png',
    });
    Object.defineProperty(fileInput.element, 'files', {
      value: [oversizedFile],
      configurable: true,
    });
    await fileInput.trigger('change');

    expect(wrapper.find('.banner--error').text()).toContain('2 MB');

    const validFile = new File([new Uint8Array(1024)], 'comprobante.png', {
      type: 'image/png',
    });
    Object.defineProperty(fileInput.element, 'files', {
      value: [validFile],
      configurable: true,
    });
    await fileInput.trigger('change');
    expect(wrapper.text()).toContain('Archivo validado: comprobante.png');

    await wrapper.find('#step-2-metodo').setValue('EFECTIVO');
    await wrapper.find('#btn-step-2-back').trigger('click');
    await wrapper.find('#select-moneda').setValue('USD');
    await wrapper.find('#step-1-monto').setValue('20.00');
    expect(wrapper.find('#badge-tipo-cobertura').text()).toContain('ABONO PARCIAL');

    await wrapper.find('#btn-step-1-next').trigger('click');
    await wrapper.find('#btn-step-2-next').trigger('click');
    await wrapper.find('#btn-step-3-back').trigger('click');
    await wrapper.find('#btn-step-2-next').trigger('click');

    const postSpy = vi
      .spyOn(apiClient, 'post')
      .mockResolvedValueOnce({
        url: '/api/evidencias/comprobantes/abc.webp',
        mime_origen: 'image/png',
        formato_destino: 'webp',
        bytes_recibidos: 1024,
        estado: 'PROCESADO',
      })
      .mockResolvedValueOnce({
        id: 91,
        recibo_id: 1,
        usuario_id: 2,
        monto: '20.00',
        moneda: 'USD',
        monto_usd: '20.00',
        tasa_cambio: '36.50',
        metodo_pago: 'EFECTIVO',
        numero_referencia: null,
        url_comprobante: '/api/evidencias/comprobantes/abc.webp',
        estado: 'EN_REVISION',
      });

    await wrapper.find('#btn-submit-pago').trigger('click');
    await flushPromises();
    expect(postSpy).toHaveBeenNthCalledWith(
      1,
      '/api/evidencias/subir?categoria=comprobantes',
      expect.any(FormData),
      expect.objectContaining({ idempotencyKey: expect.any(String) }),
    );
    expect(postSpy).toHaveBeenNthCalledWith(
      2,
      '/api/pagos/reportar',
      expect.objectContaining({
        url_comprobante: '/api/evidencias/comprobantes/abc.webp',
      }),
      expect.objectContaining({ idempotencyKey: expect.any(String) }),
    );
  });

  it('muestra estado vacío cuando no hay recibos pendientes y muestra error si falla el envío', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue([] as never);
    const wrapper = mount(PaymentWizardView);
    await flushPromises();
    expect(wrapper.text()).toContain('No tienes recibos pendientes');

    mockPendingDashboardApis();
    const wrapper2 = mount(PaymentWizardView);
    await flushPromises();
    await wrapper2.find('#btn-step-1-next').trigger('click');
    await wrapper2.find('#input-referencia').setValue('99887766');
    await wrapper2.find('#btn-step-2-next').trigger('click');
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new Error('Network error'));
    await wrapper2.find('#btn-submit-pago').trigger('click');
    await flushPromises();
    expect(wrapper2.find('.banner--error').exists()).toBe(true);
  });

  it('cubre cambios de recibo, moneda VES/USD, archivo vacío y monto <= 0', async () => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
      if (url === '/api/finanzas/tasa') {
        return { id: 1, fecha: '2026-10-29', tasa_usd_ves: '40.00' };
      }
      if (url === '/api/finanzas/resumen') {
        return {
          deuda_total_usd: '75.00',
          total_egresos_usd: '200.00',
          gastos_por_categoria: {},
          estado_cobranza: [
            {
              recibo_id: 1,
              unidad_id: 1,
              periodo: '2026-10',
              estado: 'PENDIENTE',
              saldo_usd: '50.00',
            },
            {
              recibo_id: 2,
              unidad_id: 1,
              periodo: '2026-11',
              estado: 'PENDIENTE',
              saldo_usd: '25.00',
            },
          ],
        };
      }
      return [];
    });

    const wrapper = mount(PaymentWizardView);
    await flushPromises();

    // Cambiar de recibo, resetear a VES, probar archivo vacío en paso 2 y monto <= 0
    await wrapper.find('#select-recibo').setValue('2');
    await wrapper.find('#select-moneda').setValue('USD');
    await wrapper.find('#select-moneda').setValue('VES');

    await wrapper.find('#btn-step-1-next').trigger('click');
    await wrapper.find('#step-2-metodo').setValue('EFECTIVO');
    const fileInputStep2 = wrapper.find('#step-3-comprobante');
    Object.defineProperty(fileInputStep2.element, 'files', { value: [], configurable: true });
    await fileInputStep2.trigger('change');
    await wrapper.find('#btn-step-2-next').trigger('click');
    await wrapper.find('#btn-step-3-back').trigger('click');
    await wrapper.find('#btn-step-2-back').trigger('click');

    // Monto en 0 bloquea avance / envío
    await wrapper.find('#step-1-monto').setValue('0');
    await wrapper.find('#btn-step-1-next').trigger('click');
    expect(wrapper.find('.banner--error').exists()).toBe(true);
  });

  it('ordena recibos priorizando unidad activa, tolera ausencia de tasa BCV y respeta edición manual', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 2,
      nombre: 'Ana',
      cedula: 'V-12345678',
      correo: 'ana@condominio.local',
      telefono: '04141234567',
      rol: 'PROPIETARIO',
      es_activo: true,
      unidad_activa_id: 2,
    });

    vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
      if (url === '/api/finanzas/tasa') {
        throw new Error('404 sin tasa BCV');
      }
      if (url === '/api/finanzas/resumen') {
        return {
          deuda_total_usd: '90.00',
          total_egresos_usd: '200.00',
          gastos_por_categoria: {},
          estado_cobranza: [
            {
              recibo_id: 1,
              unidad_id: 3,
              periodo: '2026-10',
              estado: 'PENDIENTE',
              saldo_usd: '30.00',
            },
            {
              recibo_id: 2,
              unidad_id: 2,
              periodo: '2026-09',
              estado: 'PENDIENTE',
              saldo_usd: '40.00',
            },
            {
              recibo_id: 3,
              unidad_id: 1,
              periodo: '2026-10',
              estado: 'PENDIENTE',
              saldo_usd: '20.00',
            },
          ],
        };
      }
      return [];
    });

    const wrapper = mount(PaymentWizardView);
    await flushPromises();

    // Sin tasa BCV cae en USD y mantiene recibo de unidad activa (recibo_id 2) primero
    expect((wrapper.find('#select-moneda').element as HTMLSelectElement).value).toBe('USD');
    expect((wrapper.find('#select-recibo').element as HTMLSelectElement).value).toBe('2');
    expect(wrapper.text()).toContain('Tasa BCV pendiente hoy');
    expect(wrapper.text()).toContain('Pendiente tasa BCV');

    // Al editar monto manualmente, cambiar a VES conserva el monto sin sobrescribir
    await wrapper.find('#step-1-monto').trigger('input');
    await wrapper.find('#step-1-monto').setValue('12.50');
    await wrapper.find('#select-moneda').setValue('VES');
    await flushPromises();
    expect((wrapper.find('#step-1-monto').element as HTMLInputElement).value).toBe('12.5');
  });
});
