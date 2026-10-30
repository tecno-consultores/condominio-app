import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../services/apiClient';
import {
  convertUsdToVes,
  convertVesToUsd,
  determinePaymentCoverage,
  useFinanceStore,
} from './financeStore';

describe('financeStore — Patrón No Destructivo, Conversiones BCV y Candado Contable', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('convierte montos entre USD y VES y determina cobertura total vs abono parcial', () => {
    expect(convertUsdToVes('50.00', '36.50')).toBe('1825.00');
    expect(convertUsdToVes(50, 36.5)).toBe('1825.00');
    expect(convertUsdToVes('invalid', '36.50')).toBe('0.00');
    expect(convertVesToUsd('365.00', '36.50')).toBe('10.00');
    expect(convertVesToUsd(365, 36.5)).toBe('10.00');
    expect(convertVesToUsd('100', '0')).toBe('0.00');

    expect(determinePaymentCoverage(50, 50)).toBe('PAGO_TOTAL');
    expect(determinePaymentCoverage(60, 50)).toBe('PAGO_TOTAL');
    expect(determinePaymentCoverage(25, 50)).toBe('ABONO_PARCIAL');
    expect(determinePaymentCoverage(0, 50)).toBe('ABONO_PARCIAL');
  });

  it('carga datos del dashboard y preserva estado previo marcando isStale=true ante fallo de red', async () => {
    const store = useFinanceStore();
    vi.spyOn(apiClient, 'get')
      .mockResolvedValueOnce({ id: 2, fecha: '2026-10-30', tasa_usd_ves: '40.00' })
      .mockResolvedValueOnce({
        deuda_total_usd: '120.00',
        total_egresos_usd: '450.00',
        gastos_por_categoria: { 'Bombas de Agua': '300.00', Vigilancia: '150.00' },
        estado_cobranza: [
          { unidad_id: 1, periodo: '2026-10', estado: 'PENDIENTE', saldo_usd: '120.00' },
        ],
      });

    await store.fetchDashboardData();
    expect(store.activeRateValue).toBe('40.00');
    expect(store.data.resumen?.deuda_total_usd).toBe('120.00');
    expect(store.isStale).toBe(false);

    // Simular caída de red posterior: NO debe destruir tasaActiva ni resumen
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new Error('Network down'));
    await store.fetchDashboardData();

    expect(store.isStale).toBe(true);
    expect(store.activeRateValue).toBe('40.00');
    expect(store.data.resumen?.deuda_total_usd).toBe('120.00');
    expect(store.errorMessage).toContain('Mostrando últimos datos conocidos');

    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new ApiError(502, 'Bad Gateway'));
    await store.fetchDashboardData();
    expect(store.errorMessage).toBe('Bad Gateway');
  });

  it('preserva pagosEnRevision ante error ApiError en fetchPagosEnRevision', async () => {
    const store = useFinanceStore();
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce([
      {
        id: 10,
        recibo_id: 1,
        usuario_id: 5,
        monto: '1825.00',
        moneda: 'VES',
        monto_usd: '50.00',
        tasa_cambio: '36.50',
        metodo_pago: 'PAGO_MOVIL',
        numero_referencia: '998877',
        url_comprobante: null,
        estado: 'EN_REVISION',
      },
    ]);

    await store.fetchPagosEnRevision();
    expect(store.data.pagosEnRevision).toHaveLength(1);

    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new ApiError(503, 'KeyDB en mantenimiento'));
    await store.fetchPagosEnRevision();

    expect(store.isStale).toBe(true);
    expect(store.data.pagosEnRevision).toHaveLength(1);
    expect(store.errorMessage).toBe('KeyDB en mantenimiento');

    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new Error('Offline'));
    await store.fetchPagosEnRevision();
    expect(store.errorMessage).toContain('Mostrando lista en caché');
  });

  it('registra tasa BCV, egreso y pago idempotente actualizando el estado', async () => {
    const store = useFinanceStore();
    vi.spyOn(apiClient, 'post')
      .mockResolvedValueOnce({ id: 5, fecha: '2026-10-30', tasa_usd_ves: '42.15' })
      .mockResolvedValueOnce({ id: 9, monto_usd: '80.00' })
      .mockResolvedValueOnce({
        id: 77,
        recibo_id: 1,
        usuario_id: 2,
        monto: '50.00',
        moneda: 'USD',
        monto_usd: '50.00',
        tasa_cambio: '42.15',
        metodo_pago: 'ZELLE',
        numero_referencia: 'ZELLE-12345',
        url_comprobante: null,
        estado: 'EN_REVISION',
      });

    const tasa = await store.registrarTasa('42.15', '2026-10-30');
    expect(tasa.tasa_usd_ves).toBe('42.15');

    const egreso = await store.registrarEgreso({
      periodo: '2026-10',
      categoria: 'Ascensores',
      descripcion: 'Mantenimiento preventivo mensual',
      monto: '80.00',
      moneda: 'USD',
    });
    expect(egreso.id).toBe(9);

    const pago = await store.reportarPago(
      {
        recibo_id: 1,
        monto: '50.00',
        moneda: 'USD',
        metodo_pago: 'ZELLE',
        numero_referencia: 'ZELLE-12345',
      },
      'idemp-uuid-001',
    );
    expect(pago.id).toBe(77);
    expect(store.data.pagosEnRevision[0]?.id).toBe(77);
  });

  it('aprueba y rechaza pagos exigiendo motivo mínimo de 5 caracteres', async () => {
    const store = useFinanceStore();
    store.data.pagosEnRevision = [
      {
        id: 11,
        recibo_id: 1,
        usuario_id: 2,
        monto: '50.00',
        moneda: 'USD',
        monto_usd: '50.00',
        tasa_cambio: '36.50',
        metodo_pago: 'ZELLE',
        numero_referencia: 'REF-11',
        url_comprobante: null,
        estado: 'EN_REVISION',
      },
      {
        id: 12,
        recibo_id: 1,
        usuario_id: 2,
        monto: '30.00',
        moneda: 'USD',
        monto_usd: '30.00',
        tasa_cambio: '36.50',
        metodo_pago: 'ZELLE',
        numero_referencia: 'REF-12',
        url_comprobante: null,
        estado: 'EN_REVISION',
      },
    ];

    await expect(store.rechazarPago(12, 'abc')).rejects.toThrow(
      'El motivo de rechazo debe tener al menos 5 caracteres.',
    );

    vi.spyOn(apiClient, 'put')
      .mockResolvedValueOnce({ ...store.data.pagosEnRevision[0], estado: 'APROBADO' })
      .mockResolvedValueOnce({ ...store.data.pagosEnRevision[1], estado: 'RECHAZADO' });

    await store.aprobarPago(11);
    expect(store.data.pagosEnRevision).toHaveLength(1);

    await store.rechazarPago(12, 'Referencia bancaria no localizada en estado de cuenta');
    expect(store.data.pagosEnRevision).toHaveLength(0);
  });

  it('ejecuta el cierre mensual (Candado Contable) y maneja HTTP 409 Conflict sin destruir datos', async () => {
    const store = useFinanceStore();
    vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
      periodo: '2026-10',
      estado: 'CERRADO',
    });

    const cierre = await store.ejecutarCierreMensual('2026-10');
    expect(cierre.estado).toBe('CERRADO');
    expect(store.isPeriodClosed).toBe(true);

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(409, 'El mes ya fue cerrado (acción inmutable)'),
    );
    await expect(store.ejecutarCierreMensual('2026-10')).rejects.toThrow(
      'El mes ya fue cerrado (acción inmutable)',
    );
    expect(store.errorMessage).toBe('El mes ya fue cerrado (acción inmutable)');
    expect(store.isPeriodClosed).toBe(true);
  });

  it('maneja errores HTTP y de red en mutaciones (registrarTasa, registrarEgreso, reportarPago, aprobarPago, rechazarPago, ejecutarCierreMensual)', async () => {
    const store = useFinanceStore();

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new ApiError(400, 'Tasa inválida'));
    await expect(store.registrarTasa('0')).rejects.toThrow('Tasa inválida');

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new Error('Fallo desconocido'));
    await expect(store.registrarTasa('36.50')).rejects.toThrow('Fallo desconocido');
    expect(store.errorMessage).toContain('No se pudo registrar la tasa BCV');

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new ApiError(400, 'Egreso rechazado'));
    await expect(
      store.registrarEgreso({
        periodo: '2026-10',
        categoria: 'Agua',
        descripcion: 'Filtro',
        monto: '10',
        moneda: 'USD',
      }),
    ).rejects.toThrow('Egreso rechazado');

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new Error('Fallo red egreso'));
    await expect(
      store.registrarEgreso({
        periodo: '2026-10',
        categoria: 'Agua',
        descripcion: 'Filtro',
        monto: '10',
        moneda: 'USD',
      }),
    ).rejects.toThrow('Fallo red egreso');

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new Error('Red caída'));
    await expect(
      store.reportarPago(
        {
          recibo_id: 1,
          monto: '10',
          moneda: 'USD',
          metodo_pago: 'EFECTIVO',
          numero_referencia: null,
        },
        'k-1',
      ),
    ).rejects.toThrow('Red caída');

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new ApiError(409, 'Duplicado'));
    await expect(
      store.reportarPago(
        {
          recibo_id: 1,
          monto: '10',
          moneda: 'USD',
          metodo_pago: 'EFECTIVO',
          numero_referencia: null,
        },
        'k-1',
      ),
    ).rejects.toThrow('Duplicado');

    vi.spyOn(apiClient, 'put').mockRejectedValueOnce(new ApiError(409, 'Pago ya conciliado'));
    await expect(store.aprobarPago(99)).rejects.toThrow('Pago ya conciliado');

    vi.spyOn(apiClient, 'put').mockRejectedValueOnce(new Error('Error red aprobar'));
    await expect(store.aprobarPago(99)).rejects.toThrow('Error red aprobar');

    vi.spyOn(apiClient, 'put').mockRejectedValueOnce(new ApiError(409, 'Periodo cerrado'));
    await expect(store.rechazarPago(99, 'Motivo válido de prueba')).rejects.toThrow(
      'Periodo cerrado',
    );

    vi.spyOn(apiClient, 'put').mockRejectedValueOnce(new Error('Error red rechazar'));
    await expect(store.rechazarPago(99, 'Motivo válido de prueba')).rejects.toThrow(
      'Error red rechazar',
    );

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new Error('Timeout cierre'));
    await expect(store.ejecutarCierreMensual('2026-11')).rejects.toThrow('Timeout cierre');
  });
});
