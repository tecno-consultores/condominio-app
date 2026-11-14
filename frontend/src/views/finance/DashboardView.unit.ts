import { flushPromises, mount } from '@vue/test-utils';
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

  it('muestra saludo personalizado, tasa BCV, pestañas de cobranza/gastos, Hero y acciones rápidas', async () => {
    const authStore = useAuthStore();
    authStore.data = {
      id: 1,
      nombre: 'Ana Pérez',
      cedula: 'V-12345678',
      correo: 'ana@condominio.local',
      telefono: '04141234567',
      rol: 'PROPIETARIO',
      es_activo: true,
      unidad_activa_id: 1,
    };

    const wrapper = mount(DashboardView);
    expect(wrapper.text()).toContain('Hola, Ana Pérez');
    expect(wrapper.find('#daily-rate-badge').text()).toContain('36.50 VES/USD');
    expect(wrapper.findComponent({ name: 'ClosingBanner' }).props('periodo')).toBe('2026-10');
    expect(wrapper.findComponent({ name: 'CollectionTrafficLight' }).props('ownUnitId')).toBe(1);
    expect(wrapper.find('#dashboard-quick-actions').exists()).toBe(true);

    await flushPromises();
    expect(wrapper.find('#hero-solvency-badge').text()).toContain('Saldo pendiente');
    await wrapper.find('#btn-hero-pagar').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/finanzas/reportar-pago');

    await wrapper.find('#tab-cobranza').trigger('click');
    await wrapper.find('#tab-gastos').trigger('click');
    expect(wrapper.find('#expenses-donut-chart').exists()).toBe(true);

    await wrapper.find('#tab-cobranza').trigger('click');
    expect(wrapper.find('#collection-traffic-light').exists()).toBe(true);

    await wrapper.find('#qa-reportar-pago').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/finanzas/reportar-pago');

    await wrapper.find('#qa-solvencia').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/finanzas/solvencia');

    await wrapper.find('#qa-consultas').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/consultas');

    await wrapper.find('#qa-incidencias').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/incidencias');

    await wrapper.find('#fab-reportar-pago').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/finanzas/reportar-pago');
  });

  it('usa saludo genérico Vecino, tarjeta hero solvente y acceso directo a solvencia cuando resumen es nulo', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('Offline'));
    const financeStore = useFinanceStore();
    financeStore.data.tasaActiva = null;
    financeStore.data.resumen = null;

    const wrapper = mount(DashboardView);
    expect(wrapper.text()).toContain('Hola, Vecino');
    expect(wrapper.text()).toContain('Solvente / Al día');
    expect(wrapper.find('#hero-solvency-badge').text()).toContain('✓');
    await wrapper.find('#btn-hero-solvencia').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/finanzas/solvencia');

    await wrapper.find('#tab-gastos').trigger('click');
    expect(wrapper.find('#expenses-donut-chart').exists()).toBe(true);
  });
});
