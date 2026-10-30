import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient } from '../../services/apiClient';
import { useAuthStore } from '../../stores/authStore';
import { useFinanceStore } from '../../stores/financeStore';
import DashboardView from './DashboardView.vue';

const pushMock = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
  useRoute: () => ({ path: '/dashboard' }),
}));

describe('DashboardView.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pushMock.mockReset();
    vi.restoreAllMocks();
    vi.spyOn(apiClient, 'get')
      .mockResolvedValueOnce({ id: 1, fecha: '2026-10-29', tasa_usd_ves: '36.50' })
      .mockResolvedValueOnce({
        deuda_total_usd: '50.00',
        total_egresos_usd: '200.00',
        gastos_por_categoria: { Vigilancia: '200.00' },
        estado_cobranza: [
          { unidad_id: 1, periodo: '2026-10', estado: 'PENDIENTE', saldo_usd: '50.00' },
        ],
      });
  });

  it('muestra saludo personalizado, tasa BCV, pestañas de cobranza/gastos y navega al wizard de pago', async () => {
    const authStore = useAuthStore();
    authStore.data = {
      id: 1,
      nombre: 'Ana Pérez',
      cedula: 'V-12345678',
      correo: 'ana@condominio.local',
      telefono: '04141234567',
      rol: 'PROPIETARIO',
      es_activo: true,
    };

    const wrapper = mount(DashboardView);
    expect(wrapper.text()).toContain('Hola, Ana Pérez');
    expect(wrapper.find('#daily-rate-badge').text()).toContain('36.50 VES/USD');

    await wrapper.find('#tab-gastos').trigger('click');
    expect(wrapper.find('#expenses-donut-chart').exists()).toBe(true);

    await wrapper.find('#tab-cobranza').trigger('click');
    expect(wrapper.find('#collection-traffic-light').exists()).toBe(true);

    await wrapper.find('#fab-reportar-pago').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/finanzas/reportar-pago');
  });

  it('usa saludo genérico Vecino y valores por defecto cuando authStore.data y resumen son nulos', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('Offline'));
    const financeStore = useFinanceStore();
    financeStore.data.tasaActiva = null;
    financeStore.data.resumen = null;

    const wrapper = mount(DashboardView);
    expect(wrapper.text()).toContain('Hola, Vecino');
    expect(wrapper.text()).toContain('Solvente / Al día');
    await wrapper.find('#tab-gastos').trigger('click');
    expect(wrapper.find('#expenses-donut-chart').exists()).toBe(true);
  });
});
