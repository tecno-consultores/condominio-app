import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError } from '../services/apiClient';
import { useAuthStore } from './authStore';
import {
  convertUsdToVes,
  convertVesToUsd,
  determinePaymentCoverage,
  useFinanceStore,
  type CertificadoSolvenciaDTO,
  type ComunicadoDTO,
  type EvidenciaUploadResponseDTO,
  type FacturarPeriodoResponseDTO,
  type FondoCondominioDTO,
  type PagoDTO,
  type ReciboDesgloseDTO,
  type ResumenFinancieroDTO,
  type TasaCambioDTO,
  type VerificarSolvenciaDTO,
} from './financeStore';

describe('financeStore — Patrón No Destructivo, Conversiones BCV y Candado Contable', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('convierte montos entre USD y VES y determina cobertura total vs abono parcial', () => {
    expect(convertUsdToVes('50.00', '36.50')).toBe('1825.00');
    expect(convertUsdToVes('1.005', '1')).toBe('1.01');
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

  it('desacopla 404 matutino en /finanzas/tasa con Promise.allSettled, carga comunicados y separa isStale en fallo de red', async () => {
    const store = useFinanceStore();
    expect(store.data.tasaActiva).toBeNull();
    expect(store.data.resumen).toBeNull();
    expect(store.activeRateValue).toBeNull();

    // Tasa ausente (HTTP 404) NO tumba el dashboard ni marca isStale
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url === '/api/finanzas/tasa') {
        throw new ApiError(404, 'Tasa BCV aún no cargada hoy');
      }
      if (url === '/api/finanzas/resumen') {
        return {
          deuda_total_usd: '120.00',
          total_egresos_usd: '450.00',
          gastos_por_categoria: { 'Bombas de Agua': '300.00', Vigilancia: '150.00' },
          estado_cobranza: [
            {
              recibo_id: 1,
              unidad_id: 1,
              periodo: '2026-10',
              estado: 'PENDIENTE',
              saldo_usd: '120.00',
            },
          ],
        };
      }
      return [
        {
          id: 3,
          titulo: 'Mantenimiento bomba',
          contenido: 'Corte programado viernes.',
          enlace_externo: 'https://condominio.example/aviso',
          activo: true,
        },
      ];
    });

    await store.fetchDashboardData();
    expect(store.data.tasaActiva).toBeNull();
    expect(store.activeRateValue).toBeNull();
    expect(store.data.resumen?.deuda_total_usd).toBe('120.00');
    expect(store.data.comunicados).toHaveLength(1);
    expect(store.isStale).toBe(false);

    // Con tasa presente actualiza tasaActiva normalmente
    vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
      if (url === '/api/finanzas/tasa') {
        return { fecha: '2026-10-30', tasa_usd_ves: '40.00' };
      }
      if (url === '/api/finanzas/resumen') {
        return store.data.resumen;
      }
      return store.data.comunicados;
    });
    await store.fetchDashboardData();
    expect(store.activeRateValue).toBe('40.00');

    // Caída de red posterior en resumen: NO destruye tasaActiva ni resumen y marca isStale=true
    vi.spyOn(apiClient, 'get').mockImplementation(async () => {
      throw new Error('Network down');
    });
    await store.fetchDashboardData();

    expect(store.isStale).toBe(true);
    expect(store.activeRateValue).toBe('40.00');
    expect(store.data.resumen?.deuda_total_usd).toBe('120.00');
    expect(store.errorMessage).toContain('Mostrando últimos datos conocidos');

    vi.spyOn(apiClient, 'get').mockRejectedValue(new ApiError(502, 'Bad Gateway'));
    await store.fetchDashboardData();
    expect(store.errorMessage).toBe('Bad Gateway');
    expect(store.isStale).toBe(true);
  });

  it('carga comunicados recientes, publica comunicado, sube evidencia FormData y resetea estado completo', async () => {
    const store = useFinanceStore();
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce([
      { id: 10, titulo: 'Asamblea', contenido: 'Convocatoria', enlace_externo: null, activo: true },
    ]);
    const list = await store.fetchComunicadosRecientes();
    expect(list).toHaveLength(1);

    vi.spyOn(apiClient, 'post')
      .mockResolvedValueOnce({
        id: 11,
        titulo: 'Fumigación',
        contenido: 'Sábado 8am',
        enlace_externo: null,
        activo: true,
      })
      .mockResolvedValueOnce({
        url: 's3://condominio/comprobantes/1.png',
        mime_origen: 'image/png',
        formato_destino: 'avif',
        bytes_recibidos: 1200,
        estado: 'ENCOLADO',
      });

    const pub = await store.publicarComunicado({ titulo: 'Fumigación', contenido: 'Sábado 8am' });
    expect(pub.id).toBe(11);
    expect(store.data.comunicados).toHaveLength(2);

    const file = new File(['png'], 'pago.png', { type: 'image/png' });
    const up = await store.subirEvidencia(file, 'comprobantes', 'idemp-ev-1');
    expect(up.estado).toBe('ENCOLADO');

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new ApiError(403, 'Solo secretaría'));
    await expect(store.publicarComunicado({ titulo: 'X', contenido: 'Y' })).rejects.toThrow(
      'Solo secretaría',
    );
    expect(store.isStale).toBe(false);

    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new ApiError(415, 'Formato inválido'));
    await expect(store.subirEvidencia(file, 'comprobantes')).rejects.toThrow('Formato inválido');
    expect(store.isStale).toBe(false);

    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new Error('Net'));
    await store.fetchComunicadosRecientes();
    expect(store.isStale).toBe(true);

    store.resetState();
    expect(store.data.comunicados).toEqual([]);
    expect(store.data.tasaActiva).toBeNull();
    expect(store.isStale).toBe(false);
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
    const postSpy = vi
      .spyOn(apiClient, 'post')
      .mockResolvedValueOnce({ id: 5, fecha: '2026-10-30', tasa_usd_ves: '42.15' })
      .mockResolvedValueOnce({ id: 9, monto_usd: '80.00' })
      .mockResolvedValueOnce({ id: 10, monto_usd: '80.00' })
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

    const egreso = await store.registrarEgreso(
      {
        periodo: '2026-10',
        categoria: 'Ascensores',
        descripcion: 'Mantenimiento preventivo mensual',
        monto: '80.00',
        moneda: 'USD',
      },
      'idemp-egreso-001',
    );
    expect(egreso.id).toBe(9);
    expect(postSpy).toHaveBeenCalledWith(
      '/api/finanzas/egresos',
      expect.objectContaining({ periodo: '2026-10', monto: '80.00' }),
      { idempotencyKey: 'idemp-egreso-001' },
    );

    const egresoAuto = await store.registrarEgreso({
      periodo: '2026-10',
      categoria: 'Ascensores',
      descripcion: 'Mantenimiento preventivo mensual',
      monto: '80.00',
      moneda: 'USD',
    });
    expect(egresoAuto).toBeDefined();
    expect(postSpy).toHaveBeenLastCalledWith(
      '/api/finanzas/egresos',
      expect.objectContaining({ periodo: '2026-10' }),
      expect.objectContaining({ idempotencyKey: expect.any(String) }),
    );

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

    const putSpy = vi
      .spyOn(apiClient, 'put')
      .mockResolvedValueOnce({ ...store.data.pagosEnRevision[0], estado: 'APROBADO' })
      .mockResolvedValueOnce({ ...store.data.pagosEnRevision[1], estado: 'RECHAZADO' });

    await store.aprobarPago(11, 'idemp-aprobar-011');
    expect(putSpy).toHaveBeenCalledWith(
      '/api/pagos/11/aprobar',
      {},
      { idempotencyKey: 'idemp-aprobar-011' },
    );
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

  it('gestiona fondos patrimoniales, facturación mensual LPH, desglose de recibos y certificados de solvencia (Hito 10)', async () => {
    const store = useFinanceStore();

    vi.spyOn(apiClient, 'get')
      .mockResolvedValueOnce([
        {
          id: 1,
          nombre: 'Fondo de Reserva Legal',
          tipo: 'RESERVA_LEGAL',
          porcentaje_recargo: '10.00',
          saldo_actual_usd: '150.00',
          es_activo: true,
        },
      ])
      .mockResolvedValueOnce({
        recibo_id: 7,
        unidad_id: 1,
        identificador_unidad: 'Apto 1-A',
        alicuota_aplicada: '25.0000',
        periodo: '2026-10',
        monto_usd: '25.00',
        monto_pagado_usd: '0.00',
        saldo_pendiente_usd: '25.00',
        credito_descontado_usd: '0.00',
        estado: 'PENDIENTE',
        bloqueado: false,
        items: [],
      })
      .mockResolvedValueOnce({
        valido: true,
        folio: 'SOLV-202610-0001-ABCD',
        unidad_id: 1,
        identificador_unidad: 'Apto 1-A',
        fecha_vencimiento: '2026-10-31',
        vigente: true,
        deuda_verificada_usd: '0.00',
        firma_hmac: 'sig123',
      });

    await store.fetchFondos();
    expect(store.data.fondos).toHaveLength(1);

    const desglose = await store.fetchReciboDesglose(7);
    expect(desglose.identificador_unidad).toBe('Apto 1-A');

    const verif = await store.verificarCertificadoSolvencia('SOLV-202610-0001-ABCD', 'sig123');
    expect(verif.valido).toBe(true);

    vi.spyOn(apiClient, 'post')
      .mockResolvedValueOnce({
        id: 2,
        nombre: 'Caja Chica',
        tipo: 'CAJA_CHICA',
        porcentaje_recargo: '5.00',
        saldo_actual_usd: '0.00',
        es_activo: true,
      })
      .mockResolvedValueOnce({
        periodo: '2026-10',
        modalidad: 'ALICUOTA',
        recibos_emitidos: 4,
        total_egresos_comunes_usd: '100.00',
        recargo_fondo_reserva_usd: '10.00',
        cuota_extraordinaria_total_usd: '0.00',
        total_facturado_bruto_usd: '110.00',
        total_credito_descontado_usd: '0.00',
        total_facturado_neto_usd: '110.00',
        superavit_conciliado_fondo_usd: '0.00',
      })
      .mockResolvedValueOnce({
        id: 1,
        folio: 'SOLV-202610-0001-ABCD',
        unidad_id: 1,
        identificador_unidad: 'Apto 1-A',
        emitido_por_id: 1,
        fecha_emision: '2026-10-30T10:00:00Z',
        fecha_vencimiento: '2026-10-31',
        deuda_verificada_usd: '0.00',
        firma_hmac: 'sig123',
        qr_token: 'payload.sig123',
      });

    await store.crearFondo(
      { nombre: 'Caja Chica', tipo: 'CAJA_CHICA', porcentaje_recargo: '5.00' },
      'idemp-f-1',
    );
    expect(store.data.fondos).toHaveLength(2);

    const fact = await store.facturarPeriodo(
      { periodo: '2026-10', modalidad: 'ALICUOTA' },
      'idemp-fact-1',
    );
    expect(fact.recibos_emitidos).toBe(4);

    const cert = await store.emitirCertificadoSolvencia(1, 'idemp-solv-1');
    expect(cert.folio).toBe('SOLV-202610-0001-ABCD');

    // Fallos de red y ApiError en Hito 10 (Catch No Destructivo)
    vi.spyOn(apiClient, 'get')
      .mockRejectedValueOnce(new Error('Err fondos'))
      .mockRejectedValueOnce(new ApiError(500, 'Err fondos api'))
      .mockRejectedValueOnce(new Error('Err desglose'))
      .mockRejectedValueOnce(new ApiError(404, 'Recibo no existe'))
      .mockRejectedValueOnce(new Error('Err verif'))
      .mockRejectedValueOnce(new ApiError(400, 'Firma inválida'));

    await store.fetchFondos();
    await store.fetchFondos();
    expect(store.data.fondos).toHaveLength(2);
    expect(store.isStale).toBe(true);

    await expect(store.fetchReciboDesglose(999)).rejects.toThrow();
    await expect(store.fetchReciboDesglose(999)).rejects.toThrow();
    await expect(store.verificarCertificadoSolvencia('X', 'Y')).rejects.toThrow();
    await expect(store.verificarCertificadoSolvencia('X', 'Y')).rejects.toThrow();

    vi.spyOn(apiClient, 'post')
      .mockRejectedValueOnce(new ApiError(409, 'Fondo duplicado'))
      .mockRejectedValueOnce(new Error('Red fondo'))
      .mockRejectedValueOnce(new ApiError(409, 'Ya facturado'))
      .mockRejectedValueOnce(new Error('Red facturar'))
      .mockRejectedValueOnce(new ApiError(409, 'Deuda pendiente'))
      .mockRejectedValueOnce(new Error('Red solvencia'));

    await expect(
      store.crearFondo({ nombre: 'X', tipo: 'ESPECIAL', porcentaje_recargo: '0' }, 'k1'),
    ).rejects.toThrow();
    await expect(
      store.crearFondo({ nombre: 'X', tipo: 'ESPECIAL', porcentaje_recargo: '0' }, 'k2'),
    ).rejects.toThrow();
    await expect(
      store.facturarPeriodo({ periodo: '2026-10', modalidad: 'ALICUOTA' }, 'k3'),
    ).rejects.toThrow();
    await expect(
      store.facturarPeriodo({ periodo: '2026-10', modalidad: 'ALICUOTA' }, 'k4'),
    ).rejects.toThrow();
    await expect(store.emitirCertificadoSolvencia(1, 'k5')).rejects.toThrow();
    await expect(store.emitirCertificadoSolvencia(1, 'k6')).rejects.toThrow();
  });

  it('mantiene isStale=false y limpia sesión ante ApiError 401 (Hito 17.2)', async () => {
    const { useAuthStore } = await import('./authStore');
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 4,
      nombre: 'Tesorero',
      cedula: 'V-4',
      correo: 't@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'TESORERO',
    });

    const store = useFinanceStore();
    vi.spyOn(apiClient, 'get').mockRejectedValue(new ApiError(401, 'Sesión revocada'));
    await store.fetchDashboardData();
    expect(store.isStale).toBe(false);
    expect(authStore.isAuthenticated).toBe(false);
  });
});

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
}

type DeferredOutcome<T> = { ok: true; value: T } | { ok: false; error: unknown; rethrows: boolean };

function createDeferred<T>(): Deferred<T> {
  let resolve: ((value: T) => void) | undefined;
  let reject: ((reason: unknown) => void) | undefined;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  if (!resolve || !reject) {
    throw new Error('Deferred initialization failed');
  }
  return { promise, resolve, reject };
}

async function assertLoadingLifecycle<T>(
  store: ReturnType<typeof useFinanceStore>,
  deferred: Deferred<T>,
  trigger: () => Promise<unknown>,
  outcome: DeferredOutcome<T>,
): Promise<void> {
  const pending = trigger();
  expect(store.isLoading).toBe(true);
  if (outcome.ok) {
    deferred.resolve(outcome.value);
    await pending;
    expect(store.isLoading).toBe(false);
    return;
  }
  deferred.reject(outcome.error);
  if (outcome.rethrows) {
    await expect(pending).rejects.toThrow();
  } else {
    await pending;
  }
  expect(store.isLoading).toBe(false);
}

function mockDashboardGet(handlers: {
  tasa: () => Promise<unknown>;
  resumen: () => Promise<unknown>;
  comunicados: () => Promise<unknown>;
}) {
  return vi.spyOn(apiClient, 'get').mockImplementation(async (url) => {
    if (url === '/api/finanzas/tasa') {
      return handlers.tasa();
    }
    if (url === '/api/finanzas/resumen') {
      return handlers.resumen();
    }
    if (url === '/api/comunicados/recientes') {
      return handlers.comunicados();
    }
    throw new Error(`Unexpected GET url: ${url}`);
  });
}

function buildPago(id: number): PagoDTO {
  return {
    id,
    recibo_id: 1,
    usuario_id: 2,
    monto: '50.00',
    moneda: 'USD',
    monto_usd: '50.00',
    tasa_cambio: '36.50',
    metodo_pago: 'ZELLE',
    numero_referencia: `REF-${id}`,
    url_comprobante: null,
    estado: 'EN_REVISION',
  };
}

const sampleResumen: ResumenFinancieroDTO = {
  deuda_total_usd: '120.00',
  total_egresos_usd: '450.00',
  gastos_por_categoria: { Vigilancia: '150.00' },
  estado_cobranza: [
    {
      recibo_id: 1,
      unidad_id: 1,
      periodo: '2026-10',
      estado: 'PENDIENTE',
      saldo_usd: '120.00',
    },
  ],
};

const sampleComunicado: ComunicadoDTO = {
  id: 3,
  titulo: 'Mantenimiento',
  contenido: 'Corte programado.',
  enlace_externo: null,
  activo: true,
};

const sampleFondo: FondoCondominioDTO = {
  id: 1,
  nombre: 'Fondo de Reserva Legal',
  tipo: 'RESERVA_LEGAL',
  porcentaje_recargo: '10.00',
  saldo_actual_usd: '150.00',
  es_activo: true,
};

const sampleEvidencia: EvidenciaUploadResponseDTO = {
  url: 's3://condominio/comprobantes/2.png',
  mime_origen: 'image/png',
  formato_destino: 'avif',
  bytes_recibidos: 1024,
  estado: 'ENCOLADO',
};

const sampleFacturacion: FacturarPeriodoResponseDTO = {
  periodo: '2026-10',
  modalidad: 'ALICUOTA',
  recibos_emitidos: 4,
  total_egresos_comunes_usd: '100.00',
  recargo_fondo_reserva_usd: '10.00',
  cuota_extraordinaria_total_usd: '0.00',
  total_facturado_bruto_usd: '110.00',
  total_credito_descontado_usd: '0.00',
  total_facturado_neto_usd: '110.00',
  superavit_conciliado_fondo_usd: '0.00',
};

const sampleDesglose: ReciboDesgloseDTO = {
  recibo_id: 7,
  unidad_id: 1,
  identificador_unidad: 'Apto 1-A',
  alicuota_aplicada: '25.0000',
  periodo: '2026-10',
  monto_usd: '25.00',
  monto_pagado_usd: '0.00',
  saldo_pendiente_usd: '25.00',
  credito_descontado_usd: '0.00',
  estado: 'PENDIENTE',
  bloqueado: false,
  items: [],
};

const sampleCertificado: CertificadoSolvenciaDTO = {
  id: 1,
  folio: 'SOLV-202610-0001-ABCD',
  unidad_id: 1,
  identificador_unidad: 'Apto 1-A',
  emitido_por_id: 1,
  fecha_emision: '2026-10-30T10:00:00Z',
  fecha_vencimiento: '2026-10-31',
  deuda_verificada_usd: '0.00',
  firma_hmac: 'sig123',
  qr_token: 'payload.sig123',
};

const sampleVerificacion: VerificarSolvenciaDTO = {
  valido: true,
  folio: 'SOLV-202610-0001-ABCD',
  unidad_id: 1,
  identificador_unidad: 'Apto 1-A',
  fecha_vencimiento: '2026-10-31',
  vigente: true,
  deuda_verificada_usd: '0.00',
  firma_hmac: 'sig123',
};

describe('financeStore — Mutantes 11X: Estados, Guardas, Caché y Carga', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it('inicializa estado limpio, valida isPeriodClosed, limpia isLoading en resetState y cubre límites decimales', () => {
    const store = useFinanceStore();
    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(store.errorMessage).toBeNull();
    expect(store.lastUpdatedAt).toBeNull();
    expect(store.isPeriodClosed).toBe(false);
    expect(store.data).toEqual({
      tasaActiva: null,
      resumen: null,
      pagosEnRevision: [],
      comunicados: [],
      ultimoCierre: null,
      fondos: [],
      ultimaFacturacion: null,
      desgloseActivo: null,
      certificadoSolvenciaActivo: null,
      verificacionSolvencia: null,
    });

    store.data.ultimoCierre = { periodo: '2026-10', estado: 'PRELIMINAR' };
    expect(store.isPeriodClosed).toBe(false);
    store.data.ultimoCierre = { periodo: '2026-10', estado: 'CERRADO' };
    expect(store.isPeriodClosed).toBe(true);

    store.isLoading = true;
    store.isStale = true;
    store.errorMessage = 'error previo';
    store.lastUpdatedAt = 123456;
    store.data.fondos = [sampleFondo];
    store.resetState();

    expect(store.isLoading).toBe(false);
    expect(store.isStale).toBe(false);
    expect(store.errorMessage).toBeNull();
    expect(store.lastUpdatedAt).toBeNull();
    expect(store.data.fondos).toEqual([]);
    expect(store.isPeriodClosed).toBe(false);

    expect(convertUsdToVes('50', '0')).toBe('0.00');
    expect(convertUsdToVes('50', '-36.50')).toBe('0.00');
    expect(convertVesToUsd('100', '0')).toBe('0.00');
    expect(convertVesToUsd('100', '-10')).toBe('0.00');
    expect(determinePaymentCoverage('50', '0')).toBe('ABONO_PARCIAL');
    expect(determinePaymentCoverage('50', '-10')).toBe('ABONO_PARCIAL');
    expect(determinePaymentCoverage('0', '0')).toBe('ABONO_PARCIAL');
    expect(determinePaymentCoverage('invalid', '50')).toBe('ABONO_PARCIAL');
  });

  it('evalúa hasDashboardCache de forma exacta ante tienda vacía y caché parcial en fetchDashboardData', async () => {
    const store = useFinanceStore();
    const getSpy = vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('Network down'));

    await store.fetchDashboardData();
    expect(getSpy).toHaveBeenCalledWith('/api/finanzas/tasa');
    expect(getSpy).toHaveBeenCalledWith('/api/finanzas/resumen');
    expect(getSpy).toHaveBeenCalledWith('/api/comunicados/recientes');
    expect(store.isStale).toBe(false);
    expect(store.errorMessage).toBe(
      'No se pudo sincronizar el resumen financiero. Mostrando últimos datos conocidos.',
    );

    store.resetState();
    store.data.tasaActiva = { fecha: '2026-10-30', tasa_usd_ves: '40.00' };
    await store.fetchDashboardData();
    expect(store.isStale).toBe(true);

    store.resetState();
    store.data.resumen = sampleResumen;
    await store.fetchDashboardData();
    expect(store.isStale).toBe(true);

    store.resetState();
    store.data.comunicados = [sampleComunicado];
    await store.fetchDashboardData();
    expect(store.isStale).toBe(true);
  });

  it('gestiona tasa 404 vs 500/no-ApiError, payloads nulos y no-arreglo en fetchDashboardData', async () => {
    const store = useFinanceStore();
    store.data.tasaActiva = { fecha: '2026-10-30', tasa_usd_ves: '40.00' };
    store.data.comunicados = [sampleComunicado];
    store.data.resumen = sampleResumen;

    mockDashboardGet({
      tasa: async () => {
        throw new ApiError(404, 'Sin tasa hoy');
      },
      resumen: async () => sampleResumen,
      comunicados: async () => null,
    });
    await store.fetchDashboardData();
    expect(store.data.tasaActiva).toBeNull();
    expect(store.data.comunicados).toEqual([sampleComunicado]);
    expect(store.isStale).toBe(false);

    store.data.tasaActiva = { fecha: '2026-10-30', tasa_usd_ves: '40.00' };
    mockDashboardGet({
      tasa: async () => {
        throw new ApiError(500, 'Error BCV');
      },
      resumen: async () => sampleResumen,
      comunicados: async () => [],
    });
    await store.fetchDashboardData();
    expect(store.data.tasaActiva?.tasa_usd_ves).toBe('40.00');

    mockDashboardGet({
      tasa: async () => {
        throw Object.assign(new Error('Not ApiError'), { status: 404 });
      },
      resumen: async () => null,
      comunicados: async () => [],
    });
    await store.fetchDashboardData();
    expect(store.data.tasaActiva?.tasa_usd_ves).toBe('40.00');
    expect(store.data.resumen).toEqual(sampleResumen);
    expect(store.errorMessage).toBeNull();
    expect(store.isStale).toBe(false);

    mockDashboardGet({
      tasa: async () => null,
      resumen: async () => sampleResumen,
      comunicados: async () => [],
    });
    await store.fetchDashboardData();
    expect(store.data.tasaActiva?.tasa_usd_ves).toBe('40.00');
  });

  it('aborta fetchDashboardData ante 401 parcial en comunicados y controla isLoading', async () => {
    const authStore = useAuthStore();
    authStore.setProfileForTesting({
      id: 4,
      nombre: 'Tesorero',
      cedula: 'V-4',
      correo: 't@test.com',
      telefono: '0414',
      es_activo: true,
      rol: 'TESORERO',
    });
    const store = useFinanceStore();

    mockDashboardGet({
      tasa: async () => ({ fecha: '2026-10-30', tasa_usd_ves: '40.00' }),
      resumen: async () => sampleResumen,
      comunicados: async () => {
        throw new ApiError(401, 'Sesión expirada en comunicados');
      },
    });
    await store.fetchDashboardData();
    expect(authStore.isAuthenticated).toBe(false);
    expect(store.isStale).toBe(false);
    expect(store.errorMessage).toBe('Sesión expirada en comunicados');
    expect(store.data.resumen).toBeNull();
    expect(store.data.tasaActiva).toBeNull();
    expect(store.isLoading).toBe(false);

    const deferred = createDeferred<unknown>();
    vi.spyOn(apiClient, 'get').mockReturnValue(deferred.promise);
    await assertLoadingLifecycle(store, deferred, () => store.fetchDashboardData(), {
      ok: false,
      error: new Error('Red lenta'),
      rethrows: false,
    });
    expect(store.isStale).toBe(false);
    expect(store.errorMessage).toBe(
      'No se pudo sincronizar el resumen financiero. Mostrando últimos datos conocidos.',
    );
  });

  it('verifica comunicados recientes (no-arreglo y caché), publicarComunicado y subirEvidencia FormData', async () => {
    const store = useFinanceStore();
    const getSpy = vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new Error('Net com'));

    const emptyList = await store.fetchComunicadosRecientes();
    expect(emptyList).toEqual([]);
    expect(getSpy).toHaveBeenCalledWith('/api/comunicados/recientes');
    expect(store.isStale).toBe(false);
    expect(store.errorMessage).toBe('No se pudieron cargar los comunicados recientes.');
    expect(store.isLoading).toBe(false);

    const dCom = createDeferred<unknown>();
    getSpy.mockReturnValueOnce(dCom.promise);
    store.isStale = true;
    await assertLoadingLifecycle(store, dCom, () => store.fetchComunicadosRecientes(), {
      ok: true,
      value: null,
    });
    expect(store.data.comunicados).toEqual([]);
    expect(store.isStale).toBe(false);

    const dPub = createDeferred<ComunicadoDTO>();
    const postSpy = vi.spyOn(apiClient, 'post').mockReturnValueOnce(dPub.promise);
    store.isStale = true;
    await assertLoadingLifecycle(
      store,
      dPub,
      () => store.publicarComunicado({ titulo: 'Aviso', contenido: 'Texto' }, 'idemp-pub-1'),
      { ok: true, value: sampleComunicado },
    );
    expect(postSpy).toHaveBeenCalledWith(
      '/api/comunicados',
      { titulo: 'Aviso', contenido: 'Texto' },
      { idempotencyKey: 'idemp-pub-1' },
    );
    expect(store.isStale).toBe(false);

    const dPubErr = createDeferred<ComunicadoDTO>();
    postSpy.mockReturnValueOnce(dPubErr.promise);
    await assertLoadingLifecycle(
      store,
      dPubErr,
      () => store.publicarComunicado({ titulo: 'X', contenido: 'Y' }),
      { ok: false, error: new Error('Net pub'), rethrows: true },
    );
    expect(store.errorMessage).toBe('No se pudo publicar el comunicado oficial.');

    postSpy.mockClear();
    const file = new File(['png'], 'recibo.png', { type: 'image/png' });
    const dEv = createDeferred<EvidenciaUploadResponseDTO>();
    postSpy.mockReturnValueOnce(dEv.promise);
    store.isStale = true;
    await assertLoadingLifecycle(
      store,
      dEv,
      () => store.subirEvidencia(file, 'comprobantes', 'idemp-ev-2'),
      { ok: true, value: sampleEvidencia },
    );
    expect(store.isStale).toBe(false);
    const [uploadUrl, uploadBody, uploadOpts] = postSpy.mock.calls[0];
    expect(uploadUrl).toBe('/api/evidencias/subir?categoria=comprobantes');
    expect(uploadBody).toBeInstanceOf(FormData);
    expect((uploadBody as FormData).get('archivo')).toBe(file);
    expect(uploadOpts).toEqual({ idempotencyKey: 'idemp-ev-2' });

    const dEvErr = createDeferred<EvidenciaUploadResponseDTO>();
    postSpy.mockReturnValueOnce(dEvErr.promise);
    await assertLoadingLifecycle(store, dEvErr, () => store.subirEvidencia(file, 'comprobantes'), {
      ok: false,
      error: new Error('Net upload'),
      rethrows: true,
    });
    expect(store.errorMessage).toBe('No se pudo subir el archivo de evidencia.');
  });

  it('controla isLoading, isStale, payloads y errores en pagos en revisión, tasa, egreso y reportarPago', async () => {
    const store = useFinanceStore();
    const getSpy = vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new Error('Offline'));
    await store.fetchPagosEnRevision();
    expect(getSpy).toHaveBeenCalledWith('/api/pagos/revision');
    expect(store.isStale).toBe(false);
    expect(store.errorMessage).toBe(
      'Error al consultar pagos en revisión. Mostrando lista en caché.',
    );
    expect(store.isLoading).toBe(false);

    const dPagos = createDeferred<PagoDTO[]>();
    getSpy.mockReturnValueOnce(dPagos.promise);
    store.isStale = true;
    await assertLoadingLifecycle(store, dPagos, () => store.fetchPagosEnRevision(), {
      ok: true,
      value: [buildPago(1)],
    });
    expect(store.isStale).toBe(false);

    const dTasa = createDeferred<TasaCambioDTO>();
    const postSpy = vi.spyOn(apiClient, 'post').mockReturnValueOnce(dTasa.promise);
    store.isStale = true;
    await assertLoadingLifecycle(
      store,
      dTasa,
      () => store.registrarTasa('42.15', '2026-10-30', 'idemp-tasa-1'),
      { ok: true, value: { id: 5, fecha: '2026-10-30', tasa_usd_ves: '42.15' } },
    );
    expect(postSpy).toHaveBeenCalledWith(
      '/api/finanzas/tasa',
      { tasa_usd_ves: '42.15', fecha: '2026-10-30' },
      { idempotencyKey: 'idemp-tasa-1' },
    );
    expect(store.isStale).toBe(false);

    postSpy.mockResolvedValueOnce({ id: 6, fecha: '2026-10-31', tasa_usd_ves: '43.00' });
    await store.registrarTasa('43.00', undefined, 'idemp-tasa-2');
    expect(postSpy).toHaveBeenCalledWith(
      '/api/finanzas/tasa',
      { tasa_usd_ves: '43.00' },
      { idempotencyKey: 'idemp-tasa-2' },
    );

    const dTasaErr = createDeferred<TasaCambioDTO>();
    postSpy.mockReturnValueOnce(dTasaErr.promise);
    await assertLoadingLifecycle(store, dTasaErr, () => store.registrarTasa('44.00'), {
      ok: false,
      error: new Error('Tasa net'),
      rethrows: true,
    });
    expect(store.errorMessage).toBe('No se pudo registrar la tasa BCV del día.');

    const dEgreso = createDeferred<{ id: number; monto_usd: string }>();
    postSpy.mockReturnValueOnce(dEgreso.promise);
    store.isStale = true;
    const egresoPayload = {
      periodo: '2026-10',
      categoria: 'Agua',
      descripcion: 'Reparación',
      monto: '25.00',
      moneda: 'USD' as const,
    };
    await assertLoadingLifecycle(
      store,
      dEgreso,
      () => store.registrarEgreso(egresoPayload, 'idemp-eg-2'),
      { ok: true, value: { id: 9, monto_usd: '25.00' } },
    );
    expect(store.isStale).toBe(false);

    const dEgresoErr = createDeferred<{ id: number; monto_usd: string }>();
    postSpy.mockReturnValueOnce(dEgresoErr.promise);
    await assertLoadingLifecycle(store, dEgresoErr, () => store.registrarEgreso(egresoPayload), {
      ok: false,
      error: new Error('Egreso net'),
      rethrows: true,
    });
    expect(store.errorMessage).toBe('No se pudo registrar el egreso.');

    const dPago = createDeferred<PagoDTO>();
    postSpy.mockReturnValueOnce(dPago.promise);
    store.isStale = true;
    const pagoPayload = {
      recibo_id: 1,
      monto: '50.00',
      moneda: 'USD' as const,
      metodo_pago: 'ZELLE' as const,
      numero_referencia: 'ZELLE-99',
    };
    await assertLoadingLifecycle(
      store,
      dPago,
      () => store.reportarPago(pagoPayload, 'idemp-rep-1'),
      { ok: true, value: buildPago(77) },
    );
    expect(store.isStale).toBe(false);
    expect(postSpy).toHaveBeenCalledWith('/api/pagos/reportar', pagoPayload, {
      idempotencyKey: 'idemp-rep-1',
    });

    const dPagoErr = createDeferred<PagoDTO>();
    postSpy.mockReturnValueOnce(dPagoErr.promise);
    await assertLoadingLifecycle(store, dPagoErr, () => store.reportarPago(pagoPayload), {
      ok: false,
      error: new Error('Pago net'),
      rethrows: true,
    });
    expect(store.errorMessage).toBe('No se pudo reportar el pago.');
  });

  it('verifica aprobarPago, rechazo con trim/longitud 5 preservando otros pagos y cierre mensual', async () => {
    const store = useFinanceStore();
    store.data.pagosEnRevision = [buildPago(11), buildPago(12)];
    store.isStale = true;

    const dAprobar = createDeferred<PagoDTO>();
    const putSpy = vi.spyOn(apiClient, 'put').mockReturnValueOnce(dAprobar.promise);
    await assertLoadingLifecycle(store, dAprobar, () => store.aprobarPago(11, 'idemp-apr-1'), {
      ok: true,
      value: { ...buildPago(11), estado: 'APROBADO' as const },
    });
    expect(store.isStale).toBe(false);
    expect(store.data.pagosEnRevision.map((p) => p.id)).toEqual([12]);

    const dAprobarErr = createDeferred<PagoDTO>();
    putSpy.mockReturnValueOnce(dAprobarErr.promise);
    await assertLoadingLifecycle(store, dAprobarErr, () => store.aprobarPago(12), {
      ok: false,
      error: new Error('Aprobar net'),
      rethrows: true,
    });
    expect(store.errorMessage).toBe('No se pudo aprobar el pago seleccionado.');

    putSpy.mockClear();
    store.isStale = true;
    await expect(store.rechazarPago(12, '  abc  ')).rejects.toThrow(
      'El motivo de rechazo debe tener al menos 5 caracteres.',
    );
    expect(putSpy).not.toHaveBeenCalled();
    expect(store.isStale).toBe(false);

    store.data.pagosEnRevision = [buildPago(11), buildPago(12)];
    store.isStale = true;
    const dRechazar = createDeferred<PagoDTO>();
    putSpy.mockReturnValueOnce(dRechazar.promise);
    await assertLoadingLifecycle(
      store,
      dRechazar,
      () => store.rechazarPago(12, '  12345  ', 'idemp-rech-5'),
      { ok: true, value: { ...buildPago(12), estado: 'RECHAZADO' as const } },
    );
    expect(putSpy).toHaveBeenCalledWith(
      '/api/pagos/12/rechazar',
      { motivo: '12345' },
      { idempotencyKey: 'idemp-rech-5' },
    );
    expect(store.data.pagosEnRevision.map((p) => p.id)).toEqual([11]);
    expect(store.isStale).toBe(false);

    const dRechazarErr = createDeferred<PagoDTO>();
    putSpy.mockReturnValueOnce(dRechazarErr.promise);
    await assertLoadingLifecycle(
      store,
      dRechazarErr,
      () => store.rechazarPago(11, 'Motivo válido'),
      { ok: false, error: new Error('Rechazar net'), rethrows: true },
    );
    expect(store.errorMessage).toBe('No se pudo rechazar el pago seleccionado.');

    const dCierre = createDeferred<{ periodo: string; estado: 'PRELIMINAR' | 'CERRADO' }>();
    const postSpy = vi.spyOn(apiClient, 'post').mockReturnValueOnce(dCierre.promise);
    store.isStale = true;
    await assertLoadingLifecycle(
      store,
      dCierre,
      () => store.ejecutarCierreMensual('2026-10', 'idemp-cierre-1'),
      { ok: true, value: { periodo: '2026-10', estado: 'CERRADO' as const } },
    );
    expect(postSpy).toHaveBeenCalledWith(
      '/api/finanzas/cierre-mensual',
      { periodo: '2026-10' },
      { idempotencyKey: 'idemp-cierre-1' },
    );
    expect(store.isStale).toBe(false);

    const dCierreErr = createDeferred<{ periodo: string; estado: 'PRELIMINAR' | 'CERRADO' }>();
    postSpy.mockReturnValueOnce(dCierreErr.promise);
    await assertLoadingLifecycle(store, dCierreErr, () => store.ejecutarCierreMensual('2026-11'), {
      ok: false,
      error: new Error('Timeout cierre'),
      rethrows: true,
    });
    expect(store.errorMessage).toBe('No se pudo ejecutar el cierre mensual (Candado Contable).');
  });

  it('verifica fondos y facturarPeriodo con URLs exactas, idempotencyKey, isLoading, isStale y errores', async () => {
    const store = useFinanceStore();
    const getSpy = vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new Error('Err fondos'));
    await store.fetchFondos();
    expect(getSpy).toHaveBeenCalledWith('/api/finanzas/fondos');
    expect(store.isStale).toBe(false);
    expect(store.errorMessage).toBe(
      'No se pudieron sincronizar los fondos patrimoniales. Mostrando datos en caché.',
    );
    expect(store.isLoading).toBe(false);

    const dFondos = createDeferred<FondoCondominioDTO[]>();
    getSpy.mockReturnValueOnce(dFondos.promise);
    store.isStale = true;
    await assertLoadingLifecycle(store, dFondos, () => store.fetchFondos(), {
      ok: true,
      value: [sampleFondo],
    });
    expect(store.isStale).toBe(false);

    getSpy.mockRejectedValueOnce(new Error('Err fondos cached'));
    await store.fetchFondos();
    expect(store.isStale).toBe(true);
    expect(store.data.fondos).toEqual([sampleFondo]);

    const dCrearFondo = createDeferred<FondoCondominioDTO>();
    const postSpy = vi.spyOn(apiClient, 'post').mockReturnValueOnce(dCrearFondo.promise);
    const fondoPayload = {
      nombre: 'Caja Chica',
      tipo: 'CAJA_CHICA' as const,
      porcentaje_recargo: '5.00',
    };
    store.isStale = true;
    await assertLoadingLifecycle(
      store,
      dCrearFondo,
      () => store.crearFondo(fondoPayload, 'idemp-fondo-1'),
      {
        ok: true,
        value: { ...sampleFondo, id: 2, nombre: 'Caja Chica', tipo: 'CAJA_CHICA' as const },
      },
    );
    expect(postSpy).toHaveBeenCalledWith('/api/finanzas/fondos', fondoPayload, {
      idempotencyKey: 'idemp-fondo-1',
    });
    expect(store.isStale).toBe(false);

    const dCrearFondoErr = createDeferred<FondoCondominioDTO>();
    postSpy.mockReturnValueOnce(dCrearFondoErr.promise);
    await assertLoadingLifecycle(store, dCrearFondoErr, () => store.crearFondo(fondoPayload), {
      ok: false,
      error: new Error('Red fondo'),
      rethrows: true,
    });
    expect(store.errorMessage).toBe('No se pudo crear el fondo patrimonial.');

    const dFact = createDeferred<FacturarPeriodoResponseDTO>();
    postSpy.mockReturnValueOnce(dFact.promise);
    const factPayload = { periodo: '2026-10', modalidad: 'ALICUOTA' as const };
    store.isStale = true;
    await assertLoadingLifecycle(
      store,
      dFact,
      () => store.facturarPeriodo(factPayload, 'idemp-fact-1'),
      { ok: true, value: sampleFacturacion },
    );
    expect(postSpy).toHaveBeenCalledWith('/api/finanzas/facturar-periodo', factPayload, {
      idempotencyKey: 'idemp-fact-1',
    });
    expect(store.isStale).toBe(false);
    expect(store.data.ultimaFacturacion).toEqual(sampleFacturacion);

    const dFactErr = createDeferred<FacturarPeriodoResponseDTO>();
    postSpy.mockReturnValueOnce(dFactErr.promise);
    await assertLoadingLifecycle(store, dFactErr, () => store.facturarPeriodo(factPayload), {
      ok: false,
      error: new Error('Red facturar'),
      rethrows: true,
    });
    expect(store.errorMessage).toBe('No se pudo emitir la facturación del periodo seleccionado.');
  });

  it('verifica desglose, emisión y verificación de solvencia (trimming, encoding, isLoading, isStale y caché)', async () => {
    const store = useFinanceStore();
    const dDesgErr = createDeferred<ReciboDesgloseDTO>();
    const getSpy = vi.spyOn(apiClient, 'get').mockReturnValueOnce(dDesgErr.promise);
    await assertLoadingLifecycle(store, dDesgErr, () => store.fetchReciboDesglose(999), {
      ok: false,
      error: new Error('Err desglose empty'),
      rethrows: true,
    });
    expect(getSpy).toHaveBeenCalledWith('/api/finanzas/recibos/999/desglose');
    expect(store.isStale).toBe(false);
    expect(store.errorMessage).toBe('No se pudo consultar el desglose del recibo seleccionado.');

    const dDesg = createDeferred<ReciboDesgloseDTO>();
    getSpy.mockReturnValueOnce(dDesg.promise);
    store.isStale = true;
    await assertLoadingLifecycle(store, dDesg, () => store.fetchReciboDesglose(7), {
      ok: true,
      value: sampleDesglose,
    });
    expect(getSpy).toHaveBeenCalledWith('/api/finanzas/recibos/7/desglose');
    expect(store.isStale).toBe(false);
    expect(store.data.desgloseActivo).toEqual(sampleDesglose);

    getSpy.mockRejectedValueOnce(new Error('Err desglose cached'));
    await expect(store.fetchReciboDesglose(7)).rejects.toThrow('Err desglose cached');
    expect(store.isStale).toBe(true);
    expect(store.isLoading).toBe(false);

    const dSolv = createDeferred<CertificadoSolvenciaDTO>();
    const postSpy = vi.spyOn(apiClient, 'post').mockReturnValueOnce(dSolv.promise);
    store.isStale = true;
    await assertLoadingLifecycle(
      store,
      dSolv,
      () => store.emitirCertificadoSolvencia(1, 'idemp-solv-1'),
      { ok: true, value: sampleCertificado },
    );
    expect(postSpy).toHaveBeenCalledWith(
      '/api/finanzas/solvencia/1',
      {},
      { idempotencyKey: 'idemp-solv-1' },
    );
    expect(store.isStale).toBe(false);
    expect(store.data.certificadoSolvenciaActivo).toEqual(sampleCertificado);

    const dSolvErr = createDeferred<CertificadoSolvenciaDTO>();
    postSpy.mockReturnValueOnce(dSolvErr.promise);
    await assertLoadingLifecycle(store, dSolvErr, () => store.emitirCertificadoSolvencia(1), {
      ok: false,
      error: new Error('Red solvencia'),
      rethrows: true,
    });
    expect(store.errorMessage).toBe(
      'No se pudo emitir el Certificado de Solvencia para la unidad indicada.',
    );

    const dVerifErr = createDeferred<VerificarSolvenciaDTO>();
    getSpy.mockReturnValueOnce(dVerifErr.promise);
    await assertLoadingLifecycle(
      store,
      dVerifErr,
      () => store.verificarCertificadoSolvencia('  SOLV-1  ', '  sig+123  '),
      { ok: false, error: new Error('Err verif empty'), rethrows: true },
    );
    expect(getSpy).toHaveBeenCalledWith('/api/finanzas/solvencia/verificar/SOLV-1?sig=sig%2B123');
    expect(store.isStale).toBe(false);
    expect(store.errorMessage).toBe('No se pudo verificar el Certificado de Solvencia.');

    const dVerif = createDeferred<VerificarSolvenciaDTO>();
    getSpy.mockReturnValueOnce(dVerif.promise);
    store.isStale = true;
    await assertLoadingLifecycle(
      store,
      dVerif,
      () => store.verificarCertificadoSolvencia('  SOLV-1  ', '  sig+123  '),
      { ok: true, value: sampleVerificacion },
    );
    expect(store.isStale).toBe(false);
    expect(store.data.verificacionSolvencia).toEqual(sampleVerificacion);

    getSpy.mockRejectedValueOnce(new Error('Err verif cached'));
    await expect(store.verificarCertificadoSolvencia('SOLV-1', 'sig')).rejects.toThrow(
      'Err verif cached',
    );
    expect(store.isStale).toBe(true);
    expect(store.isLoading).toBe(false);
  });
});
