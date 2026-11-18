import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../../services/apiClient';
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
    vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
      if (url === '/api/finanzas/tasa') {
        return { id: 1, fecha: '2026-10-29', tasa_usd_ves: '36.50' };
      }
      if (url === '/api/finanzas/resumen') {
        return {
          deuda_total_usd: '50.00',
          total_egresos_usd: '200.00',
          gastos_por_categoria: { Vigilancia: '200.00' },
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
      if (url === '/api/comunicados/recientes') {
        return [{ id: 1, titulo: 'Aviso', contenido: 'Mantenimiento de ascensor' }];
      }
      if (url === '/api/estructura/unidades') {
        return [{ id: 1, identificador: 'Apto A-1', piso: 1, alicuota: '1.0000' }];
      }
      return [];
    });
  });

  it('muestra saludo personalizado, tasa BCV, pestañas ARIA, refresco manual y acciones rápidas', async () => {
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
    expect(wrapper.find('#dashboard-quick-actions').exists()).toBe(true);

    await flushPromises();
    expect(wrapper.find('#daily-rate-badge').text()).toContain('36.50 VES/USD');
    expect(wrapper.findComponent({ name: 'ClosingBanner' }).props('periodo')).toBe('2026-10');
    expect(wrapper.findComponent({ name: 'CollectionTrafficLight' }).props('ownUnitId')).toBe(1);
    expect(wrapper.findComponent({ name: 'CollectionTrafficLight' }).props('unitLabels')).toEqual({
      1: 'Apto A-1',
    });
    expect(wrapper.find('#hero-solvency-badge').text()).toContain('Saldo pendiente');
    await wrapper.find('#btn-hero-pagar').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/finanzas/reportar-pago');

    const tabCobranza = wrapper.find('#tab-cobranza');
    const tabGastos = wrapper.find('#tab-gastos');
    expect(tabCobranza.attributes('role')).toBe('tab');
    expect(tabCobranza.attributes('aria-selected')).toBe('true');

    await tabGastos.trigger('click');
    expect(tabGastos.attributes('aria-selected')).toBe('true');
    expect(wrapper.find('#expenses-donut-chart').exists()).toBe(true);

    await tabGastos.trigger('keydown', { key: 'ArrowLeft' });
    expect(tabCobranza.attributes('aria-selected')).toBe('true');
    expect(wrapper.find('#collection-traffic-light').exists()).toBe(true);

    await tabCobranza.trigger('keydown', { key: 'End' });
    expect(wrapper.find('#expenses-donut-chart').exists()).toBe(true);
    await tabGastos.trigger('keydown', { key: 'Home' });
    expect(wrapper.find('#collection-traffic-light').exists()).toBe(true);

    await wrapper.find('#btn-dual-refresh').trigger('click');
    await flushPromises();

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

  it('usa estado neutral cuando resumen es nulo y nunca afirma solvencia falsa', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('Offline'));
    const financeStore = useFinanceStore();
    financeStore.data.tasaActiva = null;
    financeStore.data.resumen = null;

    const wrapper = mount(DashboardView);
    await flushPromises();

    expect(wrapper.text()).toContain('Hola, Vecino');
    expect(wrapper.text()).toContain('Resumen financiero no disponible');
    expect(wrapper.text()).not.toContain('Solvente / Al día');
    expect(wrapper.find('#hero-solvency-badge').text()).toContain('Sin datos');
    expect(wrapper.find('#hero-solvency-badge').text()).not.toContain('✓');
    expect(wrapper.find('#daily-rate-badge').text()).toContain('Tasa BCV pendiente hoy');
    await wrapper.find('#btn-hero-refresh').trigger('click');
    await flushPromises();

    await wrapper.find('#tab-gastos').trigger('click');
    expect(wrapper.find('#expenses-donut-chart').exists()).toBe(true);
  });

  it('tolera tasa BCV 404 y muestra solvencia real cuando resumen tiene deuda cero', async () => {
    vi.spyOn(apiClient, 'get').mockImplementation(async (url: string) => {
      if (url === '/api/finanzas/tasa') {
        throw new ApiError(404, 'No hay tasa');
      }
      if (url === '/api/finanzas/resumen') {
        return {
          deuda_total_usd: '0.00',
          total_egresos_usd: '0.00',
          gastos_por_categoria: {},
          estado_cobranza: [],
        };
      }
      return [];
    });

    const wrapper = mount(DashboardView);
    await flushPromises();

    expect(wrapper.find('#daily-rate-badge').text()).toContain('Tasa BCV pendiente hoy');
    expect(wrapper.find('#hero-solvency-badge').text()).toContain('Al día');
    expect(wrapper.text()).toContain('Solvente / Al día');
    expect(wrapper.text()).toContain('Equivalente BCV: Pendiente tasa oficial');
    await wrapper.find('#btn-hero-solvencia').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/finanzas/solvencia');
  });
});
